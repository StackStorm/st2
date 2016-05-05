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

import unittest2

from st2common.models.system.action import RemoteAction
from st2common.models.system.action import RemoteScriptAction

__all__ = [
    'RemoteActionTestCase',
    'RemoteScriptActionTestCase'
]


class RemoteActionTestCase(unittest2.TestCase):
    def test_instantiation(self):
        action = RemoteAction(name='name', action_exec_id='aeid', command='ls -la',
                              env_vars={'a': 1}, on_behalf_user='onbehalf', user='user',
                              hosts=['127.0.0.1'], parallel=False, sudo=True, timeout=10)
        self.assertEqual(action.name, 'name')
        self.assertEqual(action.action_exec_id, 'aeid')
        self.assertEqual(action.command, 'ls -la')
        self.assertEqual(action.env_vars, {'a': 1})
        self.assertEqual(action.on_behalf_user, 'onbehalf')
        self.assertEqual(action.user, 'user')
        self.assertEqual(action.hosts, ['127.0.0.1'])
        self.assertEqual(action.parallel, False)
        self.assertEqual(action.sudo, True)
        self.assertEqual(action.timeout, 10)


class RemoteScriptActionTestCase(unittest2.TestCase):
    def test_instantiation(self):
        action = RemoteScriptAction(name='name', action_exec_id='aeid',
                                    script_local_path_abs='/tmp/sc/ma_script.sh',
                                    script_local_libs_path_abs='/tmp/sc/libs', named_args=None,
                                    positional_args=None, env_vars={'a': 1},
                                    on_behalf_user='onbehalf', user='user',
                                    remote_dir='/home/mauser', hosts=['127.0.0.1'],
                                    parallel=False, sudo=True, timeout=10)
        self.assertEqual(action.name, 'name')
        self.assertEqual(action.action_exec_id, 'aeid')
        self.assertEqual(action.script_local_libs_path_abs, '/tmp/sc/libs')
        self.assertEqual(action.env_vars, {'a': 1})
        self.assertEqual(action.on_behalf_user, 'onbehalf')
        self.assertEqual(action.user, 'user')
        self.assertEqual(action.remote_dir, '/home/mauser')
        self.assertEqual(action.hosts, ['127.0.0.1'])
        self.assertEqual(action.parallel, False)
        self.assertEqual(action.sudo, True)
        self.assertEqual(action.timeout, 10)

        self.assertEqual(action.script_local_dir, '/tmp/sc')
        self.assertEqual(action.script_name, 'ma_script.sh')
        self.assertEqual(action.remote_script, '/home/mauser/ma_script.sh')
        self.assertEqual(action.command, '/home/mauser/ma_script.sh')
