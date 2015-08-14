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
from st2common.models.system.action import FabricRemoteAction
from st2common.models.system.action import FabricRemoteScriptAction


class RemoteActionTestCase(unittest2.TestCase):
    def test_instantiation(self):
        action = RemoteAction(name='name', action_exec_id='aeid', command='ls -la',
                              env_vars={'a': 1}, on_behalf_user='onbehalf', user='user',
                              hosts=['localhost'], parallel=False, sudo=True, timeout=10)
        self.assertEqual(action.name, 'name')
        self.assertEqual(action.action_exec_id, 'aeid')
        self.assertEqual(action.command, 'ls -la')
        self.assertEqual(action.env_vars, {'a': 1})
        self.assertEqual(action.on_behalf_user, 'onbehalf')
        self.assertEqual(action.user, 'user')
        self.assertEqual(action.hosts, ['localhost'])
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
                                    remote_dir='/home/mauser', hosts=['localhost'],
                                    parallel=False, sudo=True, timeout=10)
        self.assertEqual(action.name, 'name')
        self.assertEqual(action.action_exec_id, 'aeid')
        self.assertEqual(action.script_local_libs_path_abs, '/tmp/sc/libs')
        self.assertEqual(action.env_vars, {'a': 1})
        self.assertEqual(action.on_behalf_user, 'onbehalf')
        self.assertEqual(action.user, 'user')
        self.assertEqual(action.remote_dir, '/home/mauser')
        self.assertEqual(action.hosts, ['localhost'])
        self.assertEqual(action.parallel, False)
        self.assertEqual(action.sudo, True)
        self.assertEqual(action.timeout, 10)

        self.assertEqual(action.script_local_dir, '/tmp/sc')
        self.assertEqual(action.script_name, 'ma_script.sh')
        self.assertEqual(action.remote_script, '/home/mauser/ma_script.sh')
        self.assertEqual(action.command, 'sudo -E -- bash -c /home/mauser/ma_script.sh')


class FabricRemoteActionTestCase(unittest2.TestCase):
    def test_fabric_remote_action_method(self):
        remote_action = FabricRemoteAction('foo', 'foo-id', 'ls -lrth', on_behalf_user='stan',
                                           parallel=True, sudo=False)
        self.assertEqual(remote_action.get_on_behalf_user(), 'stan')
        fabric_task = remote_action.get_fabric_task()
        self.assertTrue(remote_action._get_action_method() == remote_action._run)
        self.assertTrue(fabric_task is not None)
        self.assertTrue(fabric_task.wrapped == remote_action._run)

    def test_fabric_remote_action_method_sudo(self):
        remote_action = FabricRemoteAction('foo', 'foo-id', 'ls -lrth', on_behalf_user='stan',
                                           parallel=True, sudo=True)
        self.assertEqual(remote_action.get_on_behalf_user(), 'stan')
        fabric_task = remote_action.get_fabric_task()
        self.assertTrue(remote_action._get_action_method() == remote_action._sudo)
        self.assertTrue(fabric_task is not None)
        self.assertTrue(fabric_task.wrapped == remote_action._sudo)

    def test_fabric_remote_script_action_method(self):
        remote_action = FabricRemoteScriptAction('foo', 'foo-id', '/tmp/st2.py',
                                                 None,
                                                 on_behalf_user='stan',
                                                 parallel=True, sudo=False)
        self.assertEqual(remote_action.get_on_behalf_user(), 'stan')
        fabric_task = remote_action.get_fabric_task()
        self.assertTrue(fabric_task is not None)
        self.assertTrue(fabric_task.wrapped == remote_action._run_script_with_settings)

    def test_remote_dir_script_action_method_default(self):
        remote_action = FabricRemoteScriptAction('foo', 'foo-id', '/tmp/st2.py',
                                                 None,
                                                 on_behalf_user='stan',
                                                 parallel=True, sudo=False)
        self.assertEqual(remote_action.get_on_behalf_user(), 'stan')
        self.assertEqual(remote_action.remote_dir, '/tmp')
        self.assertEqual(remote_action.remote_script, '/tmp/st2.py')

    def test_remote_dir_script_action_method_override(self):
        remote_action = FabricRemoteScriptAction('foo', 'foo-id', '/tmp/st2.py',
                                                 None,
                                                 on_behalf_user='stan',
                                                 parallel=True, sudo=False, remote_dir='/foo')
        self.assertEqual(remote_action.get_on_behalf_user(), 'stan')
        self.assertEqual(remote_action.remote_dir, '/foo')
        self.assertEqual(remote_action.remote_script, '/foo/st2.py')

    def test_get_settings(self):
        # no password and private_key
        remote_action = FabricRemoteAction(name='foo', action_exec_id='foo-id',
                                           command='ls -lrth', on_behalf_user='stan',
                                           parallel=True, sudo=True,
                                           user='user')

        settings = remote_action._get_settings()
        self.assertEqual(settings['user'], 'user')
        self.assertTrue('password' not in settings)
        self.assertTrue('key_filename' not in settings)

        # password and private_key
        remote_action = FabricRemoteAction(name='foo', action_exec_id='foo-id',
                                           command='ls -lrth', on_behalf_user='stan',
                                           parallel=True, sudo=True,
                                           user='test1', password='testpass1',
                                           private_key='key_material')

        settings = remote_action._get_settings()
        self.assertEqual(settings['user'], 'test1')
        self.assertEqual(settings['password'], 'testpass1')
        self.assertTrue('/tmp/' in settings['key_filename'])
