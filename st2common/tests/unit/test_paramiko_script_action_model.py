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

from __future__ import absolute_import
import unittest

from st2common.models.system.paramiko_script_action import ParamikoRemoteScriptAction

__all__ = ["ParamikoRemoteScriptActionTestCase"]


class ParamikoRemoteScriptActionTestCase(unittest.TestCase):
    def test_get_command_string_no_env_vars(self):
        script_action = ParamikoRemoteScriptActionTestCase._get_test_script_action()
        ex = "cd /tmp && /tmp/remote_script.sh song='b s' 'taylor swift'"
        self.assertEqual(script_action.get_full_command_string(), ex)

        # Test with sudo
        script_action.sudo = True
        ex = (
            "sudo -E -- bash -c "
            + "'cd /tmp && "
            + "/tmp/remote_script.sh song='\"'\"'b s'\"'\"' '\"'\"'taylor swift'\"'\"''"
        )
        self.assertEqual(script_action.get_full_command_string(), ex)

        # with sudo password
        script_action.sudo = True
        script_action.sudo_password = "sudo pass"
        ex = (
            "set +o history ; echo -e 'sudo pass\n' | sudo -S -E -- bash -c "
            + "'cd /tmp && "
            + "/tmp/remote_script.sh song='\"'\"'b s'\"'\"' '\"'\"'taylor swift'\"'\"''"
        )
        self.assertEqual(script_action.get_full_command_string(), ex)

    def test_get_command_string_with_env_vars(self):
        script_action = ParamikoRemoteScriptActionTestCase._get_test_script_action()
        script_action.env_vars = {
            "ST2_ACTION_EXECUTION_ID": "55ce39d532ed3543aecbe71d",
            "FOO": "BAR BAZ BOOZ",
        }
        ex = (
            "export FOO='BAR BAZ BOOZ' "
            + "ST2_ACTION_EXECUTION_ID=55ce39d532ed3543aecbe71d && "
            + "cd /tmp && /tmp/remote_script.sh song='b s' 'taylor swift'"
        )
        self.assertEqual(script_action.get_full_command_string(), ex)

        # Test with sudo
        script_action.sudo = True
        ex = (
            "sudo -E -- bash -c "
            + "'export FOO='\"'\"'BAR BAZ BOOZ'\"'\"' "
            + "ST2_ACTION_EXECUTION_ID=55ce39d532ed3543aecbe71d && "
            + "cd /tmp && "
            + "/tmp/remote_script.sh song='\"'\"'b s'\"'\"' '\"'\"'taylor swift'\"'\"''"
        )
        self.assertEqual(script_action.get_full_command_string(), ex)

        # with sudo password
        script_action.sudo = True
        script_action.sudo_password = "sudo pass"

        ex = (
            "set +o history ; echo -e 'sudo pass\n' | sudo -S -E -- bash -c "
            + "'export FOO='\"'\"'BAR BAZ BOOZ'\"'\"' HISTFILE=/dev/null HISTSIZE=0 "
            + "ST2_ACTION_EXECUTION_ID=55ce39d532ed3543aecbe71d && "
            + "cd /tmp && "
            + "/tmp/remote_script.sh song='\"'\"'b s'\"'\"' '\"'\"'taylor swift'\"'\"''"
        )
        self.assertEqual(script_action.get_full_command_string(), ex)

    def test_get_command_string_no_script_args_no_env_args(self):
        script_action = ParamikoRemoteScriptActionTestCase._get_test_script_action()
        script_action.named_args = {}
        script_action.positional_args = []
        ex = "cd /tmp && /tmp/remote_script.sh"
        self.assertEqual(script_action.get_full_command_string(), ex)

        # Test with sudo
        script_action.sudo = True
        ex = "sudo -E -- bash -c " + "'cd /tmp && /tmp/remote_script.sh'"
        self.assertEqual(script_action.get_full_command_string(), ex)

    def test_get_command_string_no_script_args_with_env_args(self):
        script_action = ParamikoRemoteScriptActionTestCase._get_test_script_action()
        script_action.named_args = {}
        script_action.positional_args = []
        script_action.env_vars = {
            "ST2_ACTION_EXECUTION_ID": "55ce39d532ed3543aecbe71d",
            "FOO": "BAR BAZ BOOZ",
        }
        ex = (
            "export FOO='BAR BAZ BOOZ' "
            + "ST2_ACTION_EXECUTION_ID=55ce39d532ed3543aecbe71d && "
            + "cd /tmp && /tmp/remote_script.sh"
        )
        self.assertEqual(script_action.get_full_command_string(), ex)

        # Test with sudo
        script_action.sudo = True
        ex = (
            "sudo -E -- bash -c "
            + "'export FOO='\"'\"'BAR BAZ BOOZ'\"'\"' "
            + "ST2_ACTION_EXECUTION_ID=55ce39d532ed3543aecbe71d && "
            + "cd /tmp && "
            + "/tmp/remote_script.sh'"
        )
        self.assertEqual(script_action.get_full_command_string(), ex)

    def test_script_path_shell_injection_safe(self):
        script_action = ParamikoRemoteScriptActionTestCase._get_test_script_action()
        test_path = "/tmp/remote script.sh"
        script_action.remote_script = test_path
        script_action.named_args = {}
        script_action.positional_args = []
        ex = "cd /tmp && '/tmp/remote script.sh'"
        self.assertEqual(script_action.get_full_command_string(), ex)

        # Test with sudo
        script_action.sudo = True
        ex = "sudo -E -- bash -c " + "'cd /tmp && '\"'\"'/tmp/remote script.sh'\"'\"''"
        self.assertEqual(script_action.get_full_command_string(), ex)

        # With sudo_password
        script_action.sudo = True
        script_action.sudo_password = "sudo pass"

        ex = (
            "set +o history ; echo -e 'sudo pass\n' | sudo -S -E -- bash -c "
            + "'cd /tmp && '\"'\"'/tmp/remote script.sh'\"'\"''"
        )
        self.assertEqual(script_action.get_full_command_string(), ex)

    def test_script_path_shell_injection_safe_with_env_vars(self):
        script_action = ParamikoRemoteScriptActionTestCase._get_test_script_action()
        test_path = "/tmp/remote script.sh"
        script_action.remote_script = test_path
        script_action.named_args = {}
        script_action.positional_args = []
        script_action.env_vars = {"FOO": "BAR"}
        ex = "export FOO=BAR && cd /tmp && '/tmp/remote script.sh'"
        self.assertEqual(script_action.get_full_command_string(), ex)

        # Test with sudo
        script_action.sudo = True
        ex = (
            "sudo -E -- bash -c "
            + "'export FOO=BAR && "
            + "cd /tmp && '\"'\"'/tmp/remote script.sh'\"'\"''"
        )
        self.assertEqual(script_action.get_full_command_string(), ex)

        # With sudo_password
        script_action.sudo = True
        script_action.sudo_password = "sudo pass"

        ex = (
            "set +o history ; echo -e 'sudo pass\n' | sudo -S -E -- bash -c "
            + "'export FOO=BAR HISTFILE=/dev/null HISTSIZE=0 && "
            + "cd /tmp && '\"'\"'/tmp/remote script.sh'\"'\"''"
        )
        self.assertEqual(script_action.get_full_command_string(), ex)

    @staticmethod
    def _get_test_script_action():
        local_script_path = "/opt/stackstorm/packs/fixtures/actions/remote_script.sh"
        script_action = ParamikoRemoteScriptAction(
            "fixtures.remote_script",
            "55ce39d532ed3543aecbe71d",
            local_script_path,
            "/opt/stackstorm/packs/fixtures/actions/lib/",
            named_args={"song": "b s"},
            positional_args=["taylor swift"],
            env_vars={},
            on_behalf_user="stanley",
            user="vagrant",
            private_key="/home/vagrant/.ssh/stanley_rsa",
            remote_dir="/tmp",
            hosts=["127.0.0.1"],
            parallel=True,
            sudo=False,
            timeout=60,
            cwd="/tmp",
        )
        return script_action
