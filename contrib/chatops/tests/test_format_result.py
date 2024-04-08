# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import mock

from st2tests.base import BaseActionTestCase

from format_execution_result import FormatResultAction

__all__ = ["FormatResultActionTestCase"]


class FormatResultActionTestCase(BaseActionTestCase):
    action_cls = FormatResultAction

    def test_rendering_works_remote_shell_cmd(self):
        remote_shell_cmd_execution_model = json.loads(
            self.get_fixture_content("remote_cmd_execution.json")
        )

        action = self.get_action_instance()
        action._get_execution = mock.MagicMock(
            return_value=remote_shell_cmd_execution_model
        )
        result = action.run(execution_id="57967f9355fc8c19a96d9e4f")
        self.assertTrue(result)
        self.assertIn("web_url", result["message"])
        self.assertIn("Took 2s to complete", result["message"])

    def test_rendering_local_shell_cmd(self):
        local_shell_cmd_execution_model = json.loads(
            self.get_fixture_content("local_cmd_execution.json")
        )

        action = self.get_action_instance()
        action._get_execution = mock.MagicMock(
            return_value=local_shell_cmd_execution_model
        )
        self.assertTrue(action.run(execution_id="5799522f55fc8c2d33ac03e0"))

    def test_rendering_http_request(self):
        http_execution_model = json.loads(
            self.get_fixture_content("http_execution.json")
        )

        action = self.get_action_instance()
        action._get_execution = mock.MagicMock(return_value=http_execution_model)
        self.assertTrue(action.run(execution_id="579955f055fc8c2d33ac03e3"))

    def test_rendering_python_action(self):
        python_action_execution_model = json.loads(
            self.get_fixture_content("python_action_execution.json")
        )

        action = self.get_action_instance()
        action._get_execution = mock.MagicMock(
            return_value=python_action_execution_model
        )
        self.assertTrue(action.run(execution_id="5799572a55fc8c2d33ac03ec"))
