# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import six

from oslo_config import cfg

from st2common import log as logging
from st2common.services.config import deserialize_key_value
from st2common.persistence.pack import ConfigSchema
from st2common.persistence.pack import Config
from st2common.content import utils as content_utils
from st2common.util import jinja as jinja_utils
from st2common.util.templating import render_template_with_system_and_user_context
from st2common.util.config_parser import ContentPackConfigParser
from st2common.exceptions.db import StackStormDBObjectNotFoundError

__all__ = [
    'ContentPackConfigLoader'
]

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

        # 1. Retrieve values from pack local config.yaml file
        config = self._config_parser.get_config()

        if config:
            config = config.config or {}
            result.update(config)

        # Retrieve corresponding ConfigDB and ConfigSchemaDB object
        # Note: ConfigSchemaDB is optional right now. If it doesn't exist, we assume every value
        # is of a type string
        try:
            config_db = Config.get_by_pack(value=self.pack_name)
        except StackStormDBObjectNotFoundError:
            # Corresponding pack config doesn't exist, return early
            return result

        try:
            config_schema_db = ConfigSchema.get_by_pack(value=self.pack_name)
        except StackStormDBObjectNotFoundError:
            config_schema_db = None

        # 2. Retrieve values from "global" pack config file (if available) and resolve them if
        # necessary
        config = self._get_values_for_config(config_schema_db=config_schema_db,
                                             config_db=config_db)
        result.update(config)

        return result

    def _get_values_for_config(self, config_schema_db, config_db):
        schema_values = getattr(config_schema_db, 'attributes', {})

        result = {}
        for config_item_key, config_item_value in six.iteritems(config_db.values):
            is_jinja_expression = jinja_utils.is_jinja_expression(value=config_item_value)

            if is_jinja_expression:
                config_schema_item = schema_values.get(config_item_key, {})
                value = self._get_datastore_value_for_expression(value=config_item_value,
                    config_schema_item=config_schema_item)
                result[config_item_key] = value
            else:
                # Static value, no resolution needed
                result[config_item_key] = config_item_value

        # If config_schema is available we do a second pass and set default values for required
        # items which values are not provided / available in the config itself
        for schema_item_key, schema_item in six.iteritems(schema_values):
            default_value = schema_item.get('default', None)
            is_required = schema_item.get('required', False)

            if is_required and default_value and not result.get(schema_item_key, None):
                result[schema_item_key] = default_value

        return result

    def _get_datastore_value_for_expression(self, value, config_schema_item=None):
        """
        Retrieve datastore value by first resolving the datastore expression and then retrieving
        the value from the datastore.
        """
        config_schema_item = config_schema_item or {}
        secret = config_schema_item.get('secret', False)

        # TODO: Get key name so we can throw a more friendly exception
        value = render_template_with_system_and_user_context(value=value,
                                                             user=self.user)

        if value:
            # Deserialize the value
            value = deserialize_key_value(value=value, secret=secret)
        else:
            value = None

        return value
