import json
import mock

from st2tests.base import BaseActionTestCase

from format_execution_result import FormatResultAction

__all__ = [
    'FormatResultActionTestCase'
]


class FormatResultActionTestCase(BaseActionTestCase):
    action_cls = FormatResultAction

    def test_rendering_works_remote_shell_cmd(self):
        remote_shell_cmd_execution_model = json.loads(
            self.get_fixture_content('remote_cmd_execution.json')
        )

        action = self.get_action_instance()
        action._get_execution = mock.MagicMock(
            return_value=remote_shell_cmd_execution_model
        )
        result = action.run(execution_id='57967f9355fc8c19a96d9e4f')
        self.assertTrue(result)
        self.assertTrue('web_url' in result['message'], result['message'])
        self.assertTrue('Took 2s to complete' in result['message'], result['message'])

    def test_rendering_local_shell_cmd(self):
        local_shell_cmd_execution_model = json.loads(
            self.get_fixture_content('local_cmd_execution.json')
        )

        action = self.get_action_instance()
        action._get_execution = mock.MagicMock(
            return_value=local_shell_cmd_execution_model
        )
        self.assertTrue(action.run(execution_id='5799522f55fc8c2d33ac03e0'))

    def test_rendering_http_request(self):
        http_execution_model = json.loads(
            self.get_fixture_content('http_execution.json')
        )

        action = self.get_action_instance()
        action._get_execution = mock.MagicMock(
            return_value=http_execution_model
        )
        self.assertTrue(action.run(execution_id='579955f055fc8c2d33ac03e3'))

    def test_rendering_python_action(self):
        python_action_execution_model = json.loads(
            self.get_fixture_content('python_action_execution.json')
        )

        action = self.get_action_instance()
        action._get_execution = mock.MagicMock(
            return_value=python_action_execution_model
        )
        self.assertTrue(action.run(execution_id='5799572a55fc8c2d33ac03ec'))
