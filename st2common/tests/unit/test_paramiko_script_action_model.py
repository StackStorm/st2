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

from st2common.models.system.paramiko_script_action import ParamikoRemoteScriptAction


class ParamikoRemoteScriptActionTests(unittest2.TestCase):

    def test_get_command_string(self):
        local_script_path = '/opt/stackstorm/packs/fixtures/actions/remote_script.sh'
        script_action = ParamikoRemoteScriptAction('fixtures.remote_script',
                                                   '55ce39d532ed3543aecbe71d',
                                                   local_script_path,
                                                   '/opt/stackstorm/packs/fixtures/actions/lib/',
                                                   named_args={'stream': 'stdout'},
                                                   positional_args=[],
                                                   env_vars={},
                                                   on_behalf_user='stanley',
                                                   user='vagrant',
                                                   private_key='/home/vagrant/.ssh/stanley_rsa',
                                                   remote_dir='/tmp',
                                                   hosts=['localhost'],
                                                   parallel=True,
                                                   sudo=False,
                                                   timeout=60)
        expected_command = '/tmp/remote_script.sh stream=stdout'
        self.assertEqual(script_action.get_full_command_string(), expected_command)

        # Test with sudo
        script_action.sudo = True
        expected_command = 'sudo -E -- bash -c \'/tmp/remote_script.sh stream=stdout\''
        self.assertEqual(script_action.get_full_command_string(), expected_command)
