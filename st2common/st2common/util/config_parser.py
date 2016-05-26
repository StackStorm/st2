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

import os

import yaml

from st2common.content import utils

__all__ = [
    'ContentPackConfigParser',
    'ContentPackConfig'
]


class ContentPackConfigParser(object):
    """
    Class responsible for obtaining and parsing content pack configs.
    """

    GLOBAL_CONFIG_NAME = 'config.yaml'
    LOCAL_CONFIG_SUFFIX = '_config.yaml'

    def __init__(self, pack_name):
        self.pack_name = pack_name
        self.pack_path = utils.get_pack_base_path(pack_name=pack_name)

    def get_config(self):
        """
        Retrieve config for a particular pack.

        :return: Config object if config is found, ``None`` otherwise.
        :rtype: :class:`.ContentPackConfig` or ``None``
        """
        global_config_path = self.get_global_config_path()
        config = self.get_and_parse_config(config_path=global_config_path)

        return config

    def get_action_config(self, action_file_path):
        """
        Retrieve config for a particular action inside the content pack.

        :param action_file_path: Full absolute path to the action file.
        :type action_file_path: ``str``

        :return: Config object if config is found, ``None`` otherwise.
        :rtype: :class:`.ContentPackConfig` or ``None``
        """
        global_config_path = self.get_global_config_path()
        config = self.get_and_parse_config(config_path=global_config_path)

        return config

    def get_sensor_config(self, sensor_file_path):
        """
        Retrieve config for a particular sensor inside the content pack.

        :param sensor_file_path: Full absolute path to the sensor file.
        :type sensor_file_path: ``str``

        :return: Config object if config is found, ``None`` otherwise.
        :rtype: :class:`.ContentPackConfig` or ``None``
        """
        global_config_path = self.get_global_config_path()
        config = self.get_and_parse_config(config_path=global_config_path)

        return config

    def get_global_config_path(self):
        if not self.pack_path:
            return None

        global_config_path = os.path.join(self.pack_path,
                                          self.GLOBAL_CONFIG_NAME)
        return global_config_path

    @classmethod
    def get_and_parse_config(cls, config_path):
        if not config_path:
            return None

        if os.path.exists(config_path) and os.path.isfile(config_path):
            with open(config_path, 'r') as fp:
                config = yaml.safe_load(fp.read())

            return ContentPackConfig(file_path=config_path, config=config)

        return None

    def _get_config(self, local_config_path, global_config_path):
        for file_path in [local_config_path, global_config_path]:
            config = self.get_and_parse_config(config_path=file_path)

            if config:
                return config

        return None


class ContentPackConfig(object):
    def __init__(self, file_path, config):
        self.file_path = file_path
        self.config = config

    def __repr__(self):
        return '<ContentPackConfig file_path="%s">' % (self.file_path)
