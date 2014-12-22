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

from st2common.models.system.action import (FabricRemoteAction, FabricRemoteScriptAction)


class FabricRemoteActionsTest(unittest2.TestCase):

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
        self.assertTrue(fabric_task.wrapped == remote_action._run_script)

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
