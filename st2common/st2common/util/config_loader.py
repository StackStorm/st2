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

from st2common.services import keyvalues as keyvalue_service
from st2common.content import utils as content_utils
from st2common.util.config_parser import ContentPackConfigParser

__all__ = [
    'ContentPackConfigLoader'
]


# Prefix for datastore items which store config values
# Full keys follow this format: pack_config.<pack name>.<config key name>
# For example:
# pack_config.aws.setup.region
DATASTORE_CONFIG_KEY_PREFIX = 'pack_config'


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

    DATASTORE_KEY_SEPARATOR = '.'

    def __init__(self, pack_name):
        self.pack_name = pack_name
        self.pack_path = content_utils.get_pack_base_path(pack_name=pack_name)

        self._config_parser = ContentPackConfigParser(pack_name=pack_name)

    def get_action_config(self, action_file_path):
        result = {}

        # 1. Retrieve values from config.yaml or action local config file
        config = self._config_parser.get_action_config(action_file_path=action_file_path)

        if config:
            config = config.config or {}
            result.update(config)

        # 2. Retrieve datastore values (if available)

        return result

    def get_sensor_config(self, sensor_file_path):
        result = {}

        # 1. Retrieve values from config.yaml or sensor local config file
        config = self._config_parser.get_sensor_config(sensor_file_path=sensor_file_path)

        if config:
            config = config.config or {}
            result.update(config)

        # 2. Retreieve datastore values (if available)

        return result

    def _get_datastore_names_for_config(self, config):
        """
        Retrieve datastore key names for the provided config specifications loaded from config.yaml

        :rype: ``dict``
        """
        result = []
        for key, values in six.iteritems(config):
            key_parts = []
            key_parts.append(key)

            if isinstance(values, dict):
                # Note: To keep things simple, only one level of nesting is supported
                continue

            key_name = self.DATASTORE_KEY_SEPARATOR.join(key_parts)
            key_name = self._get_datastore_key_name(pack_name=self.pack_name,
                                                    key_name=key_name)
            result.append(key_name)

        return result

    def _get_datastore_values_for_config(self, config):
        """
        Retrieve config values from the datastore based on the provided config specifications
        loaded from config.yaml.
        """
        for key, values in six.iteritems(config):
            key_parts = []
            key_parts.append(key)

            if isinstance(values, dict):
                # Note: To keep things simple, only one level of nesting is supported
                pass

            key_name = self.DATASTORE_KEY_SEPARATOR.join(key_parts)
            key_name = self._get_datastore_key_name(pack=self.pack_name,
                                                    key_name=key_name)

            # TODO: For performance reasons use single query and "multi get"

    def _get_datastore_value(self, key_name):
        """
        Retrieve and de-serialize datastore key value.
        """
        if not result:
            return None
        pass

    def _get_datastore_key_name(self, pack_name, key_name):
        """
        Retrieve datastore key name based on the config key name.
        """
        values = []
        values.append(DATASTORE_CONFIG_KEY_PREFIX)
        values.append(pack_name)
        values.append(key_name)

        return self.DATASTORE_KEY_SEPARATOR.join(values)

    def _deserialize_key_value(self, kvp):
        """
        Deserialize the datastore item value.

        Values are serialized as a JSON object where the actual value is stored under top-level key
        value.

        This introduces some space-related overhead, but it's transparent and preferred over custom
        serialization format.
        """
        value = json.loads(kvp.value)
        value = value['value']
        return value
