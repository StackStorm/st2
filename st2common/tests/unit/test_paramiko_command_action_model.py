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

from st2common.models.system.paramiko_command_action import ParamikoRemoteCommandAction

__all__ = ["ParamikoRemoteCommandActionTestCase"]


class ParamikoRemoteCommandActionTestCase(unittest.TestCase):
    def test_get_command_string_no_env_vars(self):
        cmd_action = ParamikoRemoteCommandActionTestCase._get_test_command_action(
            "echo boo bah baz"
        )
        ex = "cd /tmp && echo boo bah baz"
        self.assertEqual(cmd_action.get_full_command_string(), ex)
        # With sudo
        cmd_action.sudo = True
        ex = "sudo -E -- bash -c 'cd /tmp && echo boo bah baz'"
        self.assertEqual(cmd_action.get_full_command_string(), ex)

        # Executing a path command requires user to provide an escaped input.
        # E.g. st2 run core.remote hosts=localhost cmd='"/tmp/space stuff.sh"'
        cmd_action = ParamikoRemoteCommandActionTestCase._get_test_command_action(
            '"/t/space stuff.sh"'
        )
        ex = 'cd /tmp && "/t/space stuff.sh"'
        self.assertEqual(cmd_action.get_full_command_string(), ex)

        # sudo_password provided
        cmd_action = ParamikoRemoteCommandActionTestCase._get_test_command_action(
            "echo boo bah baz"
        )
        cmd_action.sudo = True
        cmd_action.sudo_password = "sudo pass"

        ex = (
            "set +o history ; echo -e 'sudo pass\n' | sudo -S -E -- "
            "bash -c 'cd /tmp && echo boo bah baz'"
        )
        self.assertEqual(cmd_action.get_full_command_string(), ex)

    def test_get_command_string_with_env_vars(self):
        cmd_action = ParamikoRemoteCommandActionTestCase._get_test_command_action(
            "echo boo bah baz"
        )
        cmd_action.env_vars = {"FOO": "BAR", "BAR": "BEET CAFE"}
        ex = "export BAR='BEET CAFE' " + "FOO=BAR" + " && cd /tmp && echo boo bah baz"
        self.assertEqual(cmd_action.get_full_command_string(), ex)

        # With sudo
        cmd_action.sudo = True

        ex = (
            "sudo -E -- bash -c "
            + "'export FOO=BAR "
            + "BAR='\"'\"'BEET CAFE'\"'\"'"
            + " && cd /tmp && echo boo bah baz'"
        )
        ex = (
            "sudo -E -- bash -c "
            + "'export BAR='\"'\"'BEET CAFE'\"'\"' "
            + "FOO=BAR"
            + " && cd /tmp && echo boo bah baz'"
        )
        self.assertEqual(cmd_action.get_full_command_string(), ex)

        # with sudo_password
        cmd_action.sudo = True
        cmd_action.sudo_password = "sudo pass"
        ex = (
            "set +o history ; echo -e 'sudo pass\n' | sudo -S -E -- bash -c "
            + "'export BAR='\"'\"'BEET CAFE'\"'\"' "
            + "FOO=BAR HISTFILE=/dev/null HISTSIZE=0"
            + " && cd /tmp && echo boo bah baz'"
        )
        self.assertEqual(cmd_action.get_full_command_string(), ex)

    def test_get_command_string_no_user(self):
        cmd_action = ParamikoRemoteCommandActionTestCase._get_test_command_action(
            "echo boo bah baz"
        )
        cmd_action.user = None
        ex = "cd /tmp && echo boo bah baz"
        self.assertEqual(cmd_action.get_full_command_string(), ex)

        # Executing a path command requires user to provide an escaped input.
        cmd = 'bash "/tmp/stuff space.sh"'
        cmd_action = ParamikoRemoteCommandActionTestCase._get_test_command_action(cmd)
        cmd_action.user = None
        ex = 'cd /tmp && bash "/tmp/stuff space.sh"'
        self.assertEqual(cmd_action.get_full_command_string(), ex)

    def test_get_command_string_no_user_env_vars(self):
        cmd_action = ParamikoRemoteCommandActionTestCase._get_test_command_action(
            "echo boo bah baz"
        )
        cmd_action.user = None
        cmd_action.env_vars = {"FOO": "BAR"}
        ex = "export FOO=BAR && cd /tmp && echo boo bah baz"
        self.assertEqual(cmd_action.get_full_command_string(), ex)

    @staticmethod
    def _get_test_command_action(command):
        cmd_action = ParamikoRemoteCommandAction(
            "fixtures.remote_command",
            "55ce39d532ed3543aecbe71d",
            command=command,
            env_vars={},
            on_behalf_user="svetlana",
            user="estee",
            password=None,
            private_key="---PRIVATE-KEY---",
            hosts="127.0.0.1",
            parallel=True,
            sudo=False,
            timeout=None,
            cwd="/tmp",
        )
        return cmd_action
