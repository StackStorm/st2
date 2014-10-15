import os
import json

from st2actions.container.service import RunnerContainerService

__all__ = [
    'ContentPackConfigParser',
    'ContentPackConfig'
]


class ContentPackConfigParser(object):
    """
    Class responsible for obtaining and parsing content pack configs.
    """

    GLOBAL_CONFIG_NAME = 'config.json'
    LOCAL_CONFIG_SUFFIX = '_config.json'

    def __init__(self, content_pack_name):
        self.content_pack_name = content_pack_name
        self.content_pack_path = RunnerContainerService().get_content_pack_base_path(pack_name=content_pack_name)

    def get_action_config(self, action_file_path):
        """
        Retrieve config for a particular action inside the content pack.

        :param action_file_path: Full absolute path to the action file.
        :type action_file_path: ``str``

        :rtype: :class:`.ContentPackConfig` or ``None``
        """
        local_config_path = self._get_action_local_config_path(action_file_path=action_file_path)
        global_config_path = self._get_global_config_path()

        result = self._get_config(local_config_path=local_config_path,
                                  global_config_path=global_config_path)
        return result

    def get_sensor_config(self, sensor_file_path):
        """
        Retrieve config for a particular sensor inside the content pack.

        :param sensor_file_path: Full absolute path to the sensor file.
        :type sensor_file_path: ``str``

        :rtype: :class:`.ContentPackConfig` or ``None``
        """
        local_config_path = self._get_sensor_local_config_path(sensor_file_path=sensor_file_path)
        global_config_path = self._get_global_config_path()

        result = self._get_config(local_config_path=local_config_path,
                                  global_config_path=global_config_path)
        return result

    def _get_config(self, local_config_path, global_config_path):
        for file_path in [local_config_path, global_config_path]:
            if os.path.exists(file_path) and os.path.isfile(file_path):
                with open(file_path, 'r') as fp:
                    config = json.loads(fp.read())

                return ContentPackConfig(file_path=file_path, config=config)

        return None

    def _get_sensor_local_config_path(self, sensor_file_path):
        """
        Retrieve path to the local config for the provided sensor.

        :rtype: ``str``
        """
        dir_name, file_name = os.path.split(sensor_file_path)
        config_name = file_name.replace('.py', '_config.json')
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
        config_name = file_name.replace('.py', '_config.json')
        local_config_path = os.path.join(dir_name, config_name)
        return local_config_path

    def _get_global_config_path(self):
        global_config_path = os.path.join(self.content_pack_path,
                                          self.GLOBAL_CONFIG_NAME)
        return global_config_path


class ContentPackConfig(object):
    def __init__(self, file_path, config):
        self.file_path = file_path
        self.config = config

    def __repr__(self):
        return ('<ContentPackConfig file_path=%s>' % (self.file_path))
