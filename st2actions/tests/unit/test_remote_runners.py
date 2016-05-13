# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# XXX: FabricRunner import depends on config being setup.
import st2tests.config as tests_config
tests_config.parse_args()

from unittest2 import TestCase

from st2common.models.system.action import RemoteScriptAction


class RemoteScriptActionTestCase(TestCase):
    def test_parameter_formatting(self):
        # Only named args
        named_args = {'--foo1': 'bar1', '--foo2': 'bar2', '--foo3': True,
                      '--foo4': False}

        action = RemoteScriptAction(name='foo', action_exec_id='dummy',
                                    script_local_path_abs='test.py',
                                    script_local_libs_path_abs='/',
                                    remote_dir='/tmp',
                                    named_args=named_args, positional_args=None)
        self.assertEqual(action.command, '/tmp/test.py --foo1=bar1 --foo2=bar2 --foo3')
