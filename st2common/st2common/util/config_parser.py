import os

import yaml

from st2actions.container.service import RunnerContainerService

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
        self.pack_path = RunnerContainerService() \
            .get_pack_base_path(pack_name=pack_name)

    def get_action_config(self, action_file_path):
        """
        Retrieve config for a particular action inside the content pack.

        :param action_file_path: Full absolute path to the action file.
        :type action_file_path: ``str``

        :return: Config object if config is found, ``None`` otherwise.
        :rtype: :class:`.ContentPackConfig` or ``None``
        """
        global_config_path = self._get_global_config_path()
        config = self._get_and_parse_config(config_path=global_config_path)

        return config

    def get_sensor_config(self, sensor_file_path):
        """
        Retrieve config for a particular sensor inside the content pack.

        :param sensor_file_path: Full absolute path to the sensor file.
        :type sensor_file_path: ``str``

        :return: Config object if config is found, ``None`` otherwise.
        :rtype: :class:`.ContentPackConfig` or ``None``
        """
        global_config_path = self._get_global_config_path()
        config = self._get_and_parse_config(config_path=global_config_path)

        return config

    def _get_and_parse_config(self, config_path):
        if not config_path:
            return None

        if os.path.exists(config_path) and os.path.isfile(config_path):
                with open(config_path, 'r') as fp:
                    config = yaml.load(fp.read())

                return ContentPackConfig(file_path=config_path, config=config)

        return None

    def _get_config(self, local_config_path, global_config_path):
        for file_path in [local_config_path, global_config_path]:
            config = self._get_and_parse_config(config_path=file_path)

            if config:
                return config

        return None

    def _get_sensor_local_config_path(self, sensor_file_path):
        """
        Retrieve path to the local config for the provided sensor.

        :rtype: ``str``
        """
        dir_name, file_name = os.path.split(sensor_file_path)
        config_name = file_name.replace('.py', self.LOCAL_CONFIG_SUFFIX)
        local_config_path = os.path.join(dir_name, config_name)
        return local_config_path

    def _get_action_local_config_path(self, action_file_path):
        """
        Retrieve path to the local config for the provided Python action.

        Note: Configs are only supported for Python actions.

        :rtype: ``str``
        """
        if not action_file_path.endswith('.py'):
            raise ValueError('Only Python actions are supported')

        dir_name, file_name = os.path.split(action_file_path)
        config_name = file_name.replace('.py', self.LOCAL_CONFIG_SUFFIX)
        local_config_path = os.path.join(dir_name, config_name)
        return local_config_path

    def _get_global_config_path(self):
        if not self.pack_path:
            return None

        global_config_path = os.path.join(self.pack_path,
                                          self.GLOBAL_CONFIG_NAME)
        return global_config_path


class ContentPackConfig(object):
    def __init__(self, file_path, config):
        self.file_path = file_path
        self.config = config

    def __repr__(self):
        return ('<ContentPackConfig file_path=%s>' % (self.file_path))
