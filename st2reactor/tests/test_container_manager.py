import os

import unittest2

from st2reactor.container.manager import SensorContainerManager


class SensorContainerManagerTest(unittest2.TestCase):
    def test_get_good_config(self):
        path = os.path.join(os.path.dirname(__file__), 'resources/sample_sensor_good_config.py')
        container_manager = SensorContainerManager()
        config = container_manager._get_config(path)
        self.assertTrue(config is not None)

    def test_get_config_no_config_file(self):
        path = os.path.join(os.path.dirname(__file__), 'resources/idontexist.py')
        container_manager = SensorContainerManager()
        config = container_manager._get_config(path)
        self.assertEqual(config, {}, 'Should return empty dict')
