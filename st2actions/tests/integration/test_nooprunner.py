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

import mock

import st2tests.config as tests_config
tests_config.parse_args()

from unittest2 import TestCase
from st2actions.container.service import RunnerContainerService
from st2actions.runners import nooprunner
from st2common.constants import action as action_constants
from st2tests.fixturesloader import FixturesLoader


class TestNoopRunner(TestCase):

    fixtures_loader = FixturesLoader()

    def test_noop_command_executes(self):
        models = TestNoopRunner.fixtures_loader.load_models(
            fixtures_pack='generic', fixtures_dict={'actions': ['noop.yaml']})

        action_db = models['actions']['noop.yaml']
        runner = TestNoopRunner._get_runner(action_db)
        status, result, _ = runner.run({})

        self.assertEquals(status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertEquals(result['failed'], False)
        self.assertEquals(result['succeeded'], True)
        self.assertEquals(result['return_code'], 0)

    @staticmethod
    def _get_runner(self, action_db):
        runner = nooprunner.NoopRunner(uuid.uuid4().hex)
        runner.container_service = RunnerContainerService()
        runner.action = action_db
        runner.action_name = action_db.name
        runner.liveaction_id = uuid.uuid4().hex
        runner.entry_point = None
        runner.context = dict()
        runner.callback = dict()
        runner.libs_dir_path = None
        runner.auth_token = mock.Mock()
        runner.auth_token.token = 'mock-token'
        return runner
