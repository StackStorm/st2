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

import mock

from st2actions.runners import actionchainrunner as acr
from st2actions.container.service import RunnerContainerService
from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED
from st2common.services import action as action_service
from st2common.util import action_db as action_db_util
from st2tests import DbTestCase
from st2tests.fixturesloader import FixturesLoader


class DummyActionExecution(object):
    def __init__(self, status=LIVEACTION_STATUS_SUCCEEDED, result=''):
        self.id = None
        self.status = status
        self.result = result


FIXTURES_PACK = 'generic'

TEST_MODELS = {
    'actions': ['a1.yaml', 'a2.yaml'],
    'runners': ['testrunner1.yaml']
}

MODELS = FixturesLoader().load_models(fixtures_pack=FIXTURES_PACK,
                                      fixtures_dict=TEST_MODELS)
ACTION_1 = MODELS['actions']['a1.yaml']
ACTION_2 = MODELS['actions']['a2.yaml']
RUNNER = MODELS['runners']['testrunner1.yaml']

CHAIN_1_PATH = FixturesLoader().get_fixture_file_path_abs(
    FIXTURES_PACK, 'actionchains', 'chain_with_notifications.yaml')


@mock.patch.object(action_db_util, 'get_runnertype_by_name',
                   mock.MagicMock(return_value=RUNNER))
class TestActionChainNotifications(DbTestCase):

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'request', return_value=(DummyActionExecution(), None))
    def test_chain_runner_success_path(self, request):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_1_PATH
        chain_runner.action = ACTION_1
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        chain_runner.run({})
        self.assertNotEqual(chain_runner.chain_holder.actionchain, None)
        self.assertEqual(request.call_count, 2)
        first_call_args = request.call_args_list[0][0]
        liveaction_db = first_call_args[0]
        self.assertTrue(liveaction_db.notify, 'Notify property expected.')

        second_call_args = request.call_args_list[1][0]
        liveaction_db = second_call_args[0]
        self.assertFalse(liveaction_db.notify, 'Notify property not expected.')
