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
        self.assertTrue(action.run(execution_id='57967f9355fc8c19a96d9e4f'))

    def test_rendering_local_shell_cmd(self):
        local_shell_cmd_execution_model = json.loads(
            self.get_fixture_content('local_cmd_execution.json')
        )

        action = self.get_action_instance()
        action._get_execution = mock.MagicMock(
            return_value=local_shell_cmd_execution_model
        )
        self.assertTrue(action.run(execution_id='5799522f55fc8c2d33ac03e0'))
