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

from unittest import TestCase

# This import must be early for import-time side-effects.
import st2tests.config as tests_config

from st2common.models.system.action import RemoteScriptAction


class RemoteScriptActionTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        tests_config.parse_args()

    def test_parameter_formatting(self):
        # Only named args
        named_args = {
            "--foo1": "bar1",
            "--foo2": "bar2",
            "--foo3": True,
            "--foo4": False,
        }

        action = RemoteScriptAction(
            name="foo",
            action_exec_id="dummy",
            script_local_path_abs="test.py",
            script_local_libs_path_abs="/",
            remote_dir="/tmp",
            named_args=named_args,
            positional_args=None,
        )
        self.assertEqual(action.command, "/tmp/test.py --foo1=bar1 --foo2=bar2 --foo3")
