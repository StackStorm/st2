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

from st2common import log as logging
from st2common.services import config as config_service
from st2common.content import utils as content_utils
from st2common.util.config_parser import ContentPackConfigParser
from st2common.util.schema import get_jsonschema_type_for_value

__all__ = [
    'ContentPackConfigLoader'
]

LOG = logging.getLogger(__name__)


# If we can't infer config item type, we will fall back to this type
FALLBACK_CONFIG_VALUE_TYPE = 'string'


class ContentPackConfigLoader(object):
    """
    Class for loading / retrieving configuration for a particular pack.

    The config values are loaded and merged in the following order:

    1. Values from the config.yaml file on disk
    2. Values from the datastore based on the config.yaml structure

    In the future:

    3. Values from datastore based on the templetized datastore key names specified in the config
    template (TBD).

    This means that values from datastore have precedence over values in the config.yaml file.
    """

    def __init__(self, pack_name):
        self.pack_name = pack_name
        self.pack_path = content_utils.get_pack_base_path(pack_name=pack_name)

        self._config_parser = ContentPackConfigParser(pack_name=pack_name)

    def get_config(self):
        result = {}

        # 1. Retrieve values from config.yaml or action local config file
        config = self._config_parser.get_config()

        if config:
            config = config.config or {}
            result.update(config)

        # 2. Retrieve datastore values (if available)
        config = self._get_datastore_values_for_config(config=config)
        result.update(config)

        return result

    def _get_config_schema_for_config(self, config):
        """
        Dynamically build config schema for the provided config.

        Note: Dynamically built schema from the config.yaml file supports no nesting so flat config
        files are preferred.

        :rtype: ``dict``
        """
        result = {}

        if not config:
            return result

        for key, value in six.iteritems(config):
            datastore_name = config_service.get_datastore_key_name(pack_name=self.pack_name,
                                                                   key_name=key)
            value_type = get_jsonschema_type_for_value(value=value,
                                                       default_value=FALLBACK_CONFIG_VALUE_TYPE)

            item = {}
            item['name'] = key
            item['datastore_name'] = datastore_name
            item['type'] = value_type
            result[key] = item

        return result

    def _get_datastore_values_for_config(self, config):
        """
        Retrieve config values from the datastore based on the config schema which is dynamically
        built from the values in config.yaml file.
        """
        result = {}

        if not config:
            # No config available
            return result

        config_schema = self._get_config_schema_for_config(config=config)
        for key_name, key_value in six.iteritems(config_schema):
            # TODO: Use multi get to reduce number of queries from N to 1
            datastore_name = key_value['datastore_name']
            datastore_value = config_service.get_datastore_value(key_name=datastore_name)

            # Note: We don't include empty / None values in the result so the merging works as
            # expected (empty values are not merged in).
            if not datastore_value:
                continue

            result[key_name] = datastore_value

        return result
