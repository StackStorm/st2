import os
from unittest2 import TestCase

from oslo.config import cfg

from st2common.util.config_parser import ContentPackConfigParser
import st2tests.config as tests_config

DIRNAME = os.path.dirname(os.path.realpath(__file__))


class ContentPackConfigParserTestCase(TestCase):
    def setUp(self):
        super(ContentPackConfigParserTestCase, self).setUp()
        tests_config.parse_args()

        # Mock the packs_base_path
        mock_path = os.path.join(DIRNAME, 'fixtures/')
        cfg.CONF.content.packs_base_path = mock_path

    def test_get_action_config_inexistent_pack(self):
        parser = ContentPackConfigParser(pack_name='inexistent')
        config = parser.get_action_config(action_file_path='test.py')
        self.assertEqual(config, None)

    def test_get_action_and_sensor_config_no_config(self):
        pack_name = 'dummy_pack_1'
        parser = ContentPackConfigParser(pack_name=pack_name)

        config = parser.get_action_config(action_file_path='my_action.py')
        self.assertEqual(config, None)

        config = parser.get_sensor_config(sensor_file_path='my_sensor.py')
        self.assertEqual(config, None)

    def test_get_action_and_sensor_config_existing_config(self):
        pack_name = 'dummy_pack_2'
        parser = ContentPackConfigParser(pack_name=pack_name)

        config = parser.get_action_config(action_file_path='my_action.py')
        self.assertEqual(config.config['section1']['key1'], 'value1')
        self.assertEqual(config.config['section2']['key10'], 'value10')

        config = parser.get_sensor_config(sensor_file_path='my_sensor.py')
        self.assertEqual(config.config['section1']['key1'], 'value1')
        self.assertEqual(config.config['section2']['key10'], 'value10')
