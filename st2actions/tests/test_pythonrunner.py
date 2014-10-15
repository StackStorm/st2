import os

from unittest2 import TestCase

from st2actions.runners import pythonrunner
from st2actions.container import service
from st2common.models.api.action import ACTIONEXEC_STATUS_SUCCEEDED, ACTIONEXEC_STATUS_FAILED
import st2tests.config as tests_config

from fixtures.dummy_content_pack.actions.action_with_local_config import ActionWithLocalConfig
from fixtures.dummy_content_pack.actions.action_no_local_config import ActionNoLocalConfig
from fixtures.dummy_content_pack_2.actions.action_no_config import ActionNoConfig


PACAL_ROW_ACTION_PATH = os.path.join(os.path.dirname(
    os.path.realpath(__file__)), 'fixtures/pythonactions/pascal_row.py')


class PythonRunnerTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        tests_config.parse_args()

    def test_runner_creation(self):
        runner = pythonrunner.get_runner()
        self.assertTrue(runner is not None, 'Creation failed. No instance.')
        self.assertEqual(type(runner), pythonrunner.PythonRunner, 'Creation failed. No instance.')

    def test_simple_action(self):
        runner = pythonrunner.get_runner()
        runner.entry_point = PACAL_ROW_ACTION_PATH
        runner.container_service = service.RunnerContainerService()
        result = runner.run({'row_index': 4})
        self.assertTrue(result)
        self.assertEqual(runner.container_service.get_status(), ACTIONEXEC_STATUS_SUCCEEDED)
        self.assertEqual(runner.container_service.get_result(), [1, 4, 6, 4, 1])

    def test_simple_action_fail(self):
        runner = pythonrunner.get_runner()
        runner.entry_point = PACAL_ROW_ACTION_PATH
        runner.container_service = service.RunnerContainerService()
        result = runner.run({'row_index': '4'})
        self.assertTrue(result)
        self.assertEqual(runner.container_service.get_status(), ACTIONEXEC_STATUS_FAILED)
        import json
        print '\n', json.dumps(runner.container_service.get_result(), indent=4, sort_keys=True)

    def test_simple_action_no_file(self):
        runner = pythonrunner.get_runner()
        runner.entry_point = ''
        runner.container_service = service.RunnerContainerService()
        result = runner.run({})
        self.assertTrue(result)
        self.assertEqual(runner.container_service.get_status(), ACTIONEXEC_STATUS_FAILED)

    def test_config_parsing(self):
        # Local (action specific) config
        action = ActionWithLocalConfig()
        config = action._parse_config()

        self.assertEqual(config, {'local': 'yes', 'name': 'with_local_config'})

        # Global (content pack) config
        action = ActionNoLocalConfig()
        config = action._parse_config()

        self.assertEqual(config, {'global': 'yes', 'ponies': 'bar'})

        # No config
        action = ActionNoConfig()
        config = action._parse_config()

        self.assertEqual(config, {})
