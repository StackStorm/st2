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

import uuid
import unittest2

import st2tests.config as tests_config
tests_config.parse_args()

from unittest2 import TestCase
from st2actions.container.service import RunnerContainerService
from st2actions.runners import localrunner
from st2common.constants import action as action_constants
from st2tests.fixturesloader import FixturesLoader


class TestLocalShellRunner(TestCase):

    fixtures_loader = FixturesLoader()

    def test_shell_command_action_basic(self):
        models = TestLocalShellRunner.fixtures_loader.load_models(
            fixtures_pack='generic', fixtures_dict={'actions': ['local.json']})
        action_db = models['actions']['local.json']
        runner = TestLocalShellRunner._get_runner(action_db, cmd='echo 10')
        runner.pre_run()
        status, result, _ = runner.run({})
        runner.post_run(status, result)
        self.assertEquals(status, action_constants.ACTIONEXEC_STATUS_SUCCEEDED)
        self.assertEquals(result['stdout'], 10)

    def test_shell_script_action(self):
        models = TestLocalShellRunner.fixtures_loader.load_models(
            fixtures_pack='localrunner_pack', fixtures_dict={'actions': ['text_gen.yml']})
        action_db = models['actions']['text_gen.yml']
        entry_point = TestLocalShellRunner.fixtures_loader.get_fixture_file_path_abs(
            'localrunner_pack', 'actions', 'text_gen.py')
        runner = TestLocalShellRunner._get_runner(action_db, entry_point=entry_point)
        runner.pre_run()
        status, result, _ = runner.run({'chars': 1000})
        runner.post_run(status, result)
        self.assertEquals(status, action_constants.ACTIONEXEC_STATUS_SUCCEEDED)
        self.assertEquals(len(result['stdout']), 1000 + 1)  # +1 for the newline

    @unittest2.skip
    def test_timeout(self):
        models = TestLocalShellRunner.fixtures_loader.load_models(
            fixtures_pack='generic', fixtures_dict={'actions': ['local.json']})
        action_db = models['actions']['local.json']
        # smaller timeout == faster tests.
        runner = TestLocalShellRunner._get_runner(action_db, cmd='sleep 10', timeout=0.01)
        runner.pre_run()
        status, result, _ = runner.run({})
        runner.post_run(status, result)
        self.assertEquals(status, action_constants.ACTIONEXEC_STATUS_FAILED)

    def test_large_stdout(self):
        models = TestLocalShellRunner.fixtures_loader.load_models(
            fixtures_pack='localrunner_pack', fixtures_dict={'actions': ['text_gen.yml']})
        action_db = models['actions']['text_gen.yml']
        entry_point = TestLocalShellRunner.fixtures_loader.get_fixture_file_path_abs(
            'localrunner_pack', 'actions', 'text_gen.py')
        runner = TestLocalShellRunner._get_runner(action_db, entry_point=entry_point)
        runner.pre_run()
        char_count = 10 ** 6  # Note 10^7 succeeds but ends up being slow.
        status, result, _ = runner.run({'chars': char_count})
        runner.post_run(status, result)
        self.assertEquals(status, action_constants.ACTIONEXEC_STATUS_SUCCEEDED)
        self.assertEquals(len(result['stdout']), char_count + 1)  # +1 for the newline

    @staticmethod
    def _get_runner(action_db,
                    entry_point=None,
                    cmd=None,
                    on_behalf_user=None,
                    user=None,
                    kwarg_op=localrunner.DEFAULT_KWARG_OP,
                    timeout=localrunner.DEFAULT_ACTION_TIMEOUT,
                    sudo=False):
        runner = localrunner.LocalShellRunner(uuid.uuid4().hex)
        runner.container_service = RunnerContainerService()
        runner.action = action_db
        runner.action_name = action_db.name
        runner.action_execution_id = uuid.uuid4().hex
        runner.entry_point = entry_point
        runner.runner_parameters = {localrunner.RUNNER_COMMAND: cmd,
                                    localrunner.RUNNER_SUDO: sudo,
                                    localrunner.RUNNER_ON_BEHALF_USER: user,
                                    localrunner.RUNNER_KWARG_OP: kwarg_op,
                                    localrunner.RUNNER_TIMEOUT: timeout}
        runner.context = dict()
        runner.callback = dict()
        runner.libs_dir_path = None
        runner.auth_token = None
        return runner
