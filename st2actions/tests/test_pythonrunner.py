import tests.config
tests.config.parse_args()

import os

from st2actions.runners import pythonrunner
from st2actions.container import service
from st2common.models.api.action import ACTIONEXEC_STATUS_SUCCEEDED, ACTIONEXEC_STATUS_FAILED
from unittest2 import TestCase


PACAL_ROW_ACTION_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)),
    'fixtures/pythonactions/pascal_row.py')


class TestFabricRunnerResultStatus(TestCase):

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
