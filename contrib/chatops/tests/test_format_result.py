import mock

from st2tests.base import BaseActionTestCase

from fixtures import REMOTE_SHELL_CMD_EXECUTION_MODEL
from format_execution_result import FormatResultAction

__all__ = [
    'FormatResultActionTestCase'
]

class FormatResultActionTestCase(BaseActionTestCase):
    action_cls = FormatResultAction

    @mock.patch.object(FormatResultAction, '_get_execution', mock.MagicMock(
        return_value=REMOTE_SHELL_CMD_EXECUTION_MODEL))
    def test_rendering_works_remote_shell_cmd(self):
        action = self.get_action_instance()
        self.assertTrue(action.run(execution_id='57967f9355fc8c19a96d9e4f'))
