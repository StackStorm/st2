# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
import copy

import six

from oslo_config import cfg

from st2common import log as logging
from st2common.models.db.pack import ConfigDB
from st2common.persistence.pack import ConfigSchema
from st2common.persistence.pack import Config
from st2common.content import utils as content_utils
from st2common.util import jinja as jinja_utils
from st2common.util.templating import render_template_with_system_and_user_context
from st2common.util.config_parser import ContentPackConfigParser
from st2common.exceptions.db import StackStormDBObjectNotFoundError

__all__ = ["ContentPackConfigLoader"]

LOG = logging.getLogger(__name__)


class ContentPackConfigLoader(object):
    """
    Class which loads and resolves all the config values and returns a dictionary of resolved values
    which can be passed to the resource.

    It loads and resolves values in the following order:

    1. Static values from <pack path>/config.yaml file
    2. Dynamic and or static values from /opt/stackstorm/configs/<pack name>.yaml file.

    Values are merged from left to right which means values from "<pack name>.yaml" file have
    precedence and override values from pack local config file.
    """

    def __init__(self, pack_name, user=None):
        self.pack_name = pack_name
        self.user = user or cfg.CONF.system_user.user

        self.pack_path = content_utils.get_pack_base_path(pack_name=pack_name)
        self._config_parser = ContentPackConfigParser(pack_name=pack_name)

    def get_config(self):
        result = {}

        # Retrieve corresponding ConfigDB and ConfigSchemaDB object
        # Note: ConfigSchemaDB is optional right now. If it doesn't exist, we assume every value
        # is of a type string
        try:
            config_db = Config.get_by_pack(value=self.pack_name)
        except StackStormDBObjectNotFoundError:
            # Corresponding pack config doesn't exist. We set config_db to an empty config so
            # that the default values from config schema are still correctly applied even if
            # pack doesn't contain a config.
            config_db = ConfigDB(pack=self.pack_name, values={})

        try:
            config_schema_db = ConfigSchema.get_by_pack(value=self.pack_name)
        except StackStormDBObjectNotFoundError:
            config_schema_db = None

        # 2. Retrieve values from "global" pack config file (if available) and resolve them if
        # necessary
        config = self._get_values_for_config(
            config_schema_db=config_schema_db, config_db=config_db
        )
        result.update(config)

        return result

    def _get_values_for_config(self, config_schema_db, config_db):
        schema_values = getattr(config_schema_db, "attributes", {})
        config_values = getattr(config_db, "values", {})

        config = copy.deepcopy(config_values or {})

        # Assign dynamic config values based on the values in the datastore
        config = self._assign_dynamic_config_values(schema=schema_values, config=config)

        # If config_schema is available we do a second pass and set default values for required
        # items which values are not provided / available in the config itself
        config = self._assign_default_values(schema=schema_values, config=config)
        return config

    @staticmethod
    def _get_object_property_schema(object_schema, additional_properties_keys=None):
        """
        Create a schema for an object property using both additionalProperties and properties.

        :rtype: ``dict``
        """
        property_schema = {}
        additional_properties = object_schema.get("additionalProperties", {})
        # additionalProperties can be a boolean or a dict
        if additional_properties and isinstance(additional_properties, dict):
            # ensure that these keys are present in the object
            for key in additional_properties_keys:
                property_schema[key] = additional_properties
        property_schema.update(object_schema.get("properties", {}))
        return property_schema

    def _assign_dynamic_config_values(self, schema, config, parent_keys=None):
        """
        Assign dynamic config value for a particular config item if the ite utilizes a Jinja
        expression for dynamic config values.

        Note: This method mutates config argument in place.

        :rtype: ``dict``
        """
        parent_keys = parent_keys or []

        config_is_dict = isinstance(config, dict)
        config_is_list = isinstance(config, list)
        iterator = six.iteritems(config) if config_is_dict else enumerate(config)

        # config_item_key - if config_is_dict then this is the key in the dictionary
        #                   if config_is_list then this is the index of them item
        # config_item_value - the value of the key/index for the current item
        for config_item_key, config_item_value in iterator:
            if config_is_dict:
                # different schema for each key/value pair
                schema_item = schema.get(config_item_key, {})
            if config_is_list:
                # same schema is shared between every item in the list
                schema_item = schema

            is_dictionary = isinstance(config_item_value, dict)
            is_list = isinstance(config_item_value, list)

            # pass a copy of parent_keys so the loop doesn't add sibling keys
            current_keys = parent_keys + [str(config_item_key)]

            # Inspect nested object properties
            if is_dictionary:
                property_schema = self._get_object_property_schema(
                    schema_item,
                    additional_properties_keys=config_item_value.keys(),
                )
                self._assign_dynamic_config_values(
                    schema=property_schema,
                    config=config[config_item_key],
                    parent_keys=current_keys,
                )
            # Inspect nested list items
            elif is_list:
                self._assign_dynamic_config_values(
                    schema=schema_item.get("items", {}),
                    config=config[config_item_key],
                    parent_keys=current_keys,
                )
            else:
                is_jinja_expression = jinja_utils.is_jinja_expression(
                    value=config_item_value
                )

                if is_jinja_expression:
                    # Resolve / render the Jinja template expression
                    full_config_item_key = ".".join(current_keys)
                    value = self._get_datastore_value_for_expression(
                        key=full_config_item_key,
                        value=config_item_value,
                        config_schema_item=schema_item,
                    )

                    config[config_item_key] = value
                else:
                    # Static value, no resolution needed
                    config[config_item_key] = config_item_value

        return config

    def _assign_default_values(self, schema, config):
        """
        Assign default values for particular config if default values are provided in the config
        schema and a value is not specified in the config.

        Note: This method mutates config argument in place.

        :rtype: ``dict``
        """
        for schema_item_key, schema_item in six.iteritems(schema):
            has_default_value = "default" in schema_item
            has_config_value = schema_item_key in config

            default_value = schema_item.get("default", None)
            is_object = schema_item.get("type", None) == "object"
            has_properties = schema_item.get("properties", None)
            has_additional_properties = schema_item.get("additionalProperties", None)

            if has_default_value and not has_config_value:
                # Config value is not provided, but default value is, use a default value
                config[schema_item_key] = default_value

            # Inspect nested object properties
            if is_object and (has_properties or has_additional_properties):
                if not config.get(schema_item_key, None):
                    config[schema_item_key] = {}

                property_schema = self._get_object_property_schema(
                    schema_item,
                    additional_properties_keys=config[schema_item_key].keys(),
                )

                self._assign_default_values(
                    schema=property_schema, config=config[schema_item_key]
                )

        return config

    def _get_datastore_value_for_expression(self, key, value, config_schema_item=None):
        """
        Retrieve datastore value by first resolving the datastore expression and then retrieving
        the value from the datastore.

        :param key: Full path to the config item key (e.g. "token" / "auth.settings.token", etc.)
        """
        from st2common.services.config import deserialize_key_value

        config_schema_item = config_schema_item or {}
        secret = config_schema_item.get("secret", False)

        try:
            value = render_template_with_system_and_user_context(
                value=value, user=self.user
            )
        except Exception as e:
            # Throw a more user-friendly exception on failed render
            exc_class = type(e)
            original_msg = six.text_type(e)
            msg = (
                'Failed to render dynamic configuration value for key "%s" with value '
                '"%s" for pack "%s" config: %s %s '
                % (key, value, self.pack_name, exc_class, original_msg)
            )
            raise RuntimeError(msg)

        if value:
            # Deserialize the value
            value = deserialize_key_value(value=value, secret=secret)
        else:
            value = None

        return value


def get_config(pack, user):
    """Returns config for given pack and user."""
    LOG.debug('Attempting to get config for pack "%s" and user "%s"' % (pack, user))
    if pack and user:
        LOG.debug("Pack and user found. Loading config.")
        config_loader = ContentPackConfigLoader(pack_name=pack, user=user)

        config = config_loader.get_config()

    else:
        config = {}

    LOG.debug("Config: %s", config)

    return config
