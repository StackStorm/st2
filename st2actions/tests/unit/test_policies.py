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

import copy

import mock
import six

import st2actions.bootstrap.runnersregistrar as runners_registrar
from st2actions.runners.localrunner import LocalShellRunner
from st2common.constants import action as action_constants
from st2common.models.api.action import ActionAPI
from st2common.models.api.policy import PolicyTypeAPI, PolicyAPI
from st2common.models.db.action import LiveActionDB
from st2common.persistence.action import Action, LiveAction
from st2common.persistence.policy import PolicyType, Policy
from st2common.services import action as action_service
from st2common.transport.liveaction import LiveActionPublisher
from st2common.transport.publishers import CUDPublisher
from st2tests import DbTestCase
from st2tests.fixtures import executions
from st2tests.fixturesloader import FixturesLoader
from st2tests.policies.concurrency import ConcurrencyPolicy
from tests.unit.base import MockLiveActionPublisher


TEST_POLICY_MODULE = 'st2tests.policies.concurrency'

TEST_FIXTURES = {
    'policytypes': [
        'policy_type_1.yaml'
    ],
    'policies': [
        'policy_1.yaml'
    ]
}

PACK = 'generic'
LOADER = FixturesLoader()
FIXTURES = LOADER.load_fixtures(fixtures_pack=PACK, fixtures_dict=TEST_FIXTURES)


@mock.patch.object(
    LocalShellRunner, 'run',
    mock.MagicMock(return_value=(action_constants.LIVEACTION_STATUS_SUCCEEDED, 'non-empty', None)))
@mock.patch.object(
    CUDPublisher, 'publish_update',
    mock.MagicMock(return_value=None))
@mock.patch.object(
    CUDPublisher, 'publish_create',
    mock.MagicMock(side_effect=MockLiveActionPublisher.publish_create))
@mock.patch.object(
    LiveActionPublisher, 'publish_state',
    mock.MagicMock(side_effect=MockLiveActionPublisher.publish_state))
class SchedulingPolicyTest(DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(SchedulingPolicyTest, cls).setUpClass()

        runners_registrar.register_runner_types()
        action_local = ActionAPI(**copy.deepcopy(executions.ARTIFACTS['actions']['local']))
        Action.add_or_update(ActionAPI.to_model(action_local))

        for _, fixture in six.iteritems(FIXTURES['policytypes']):
            fixture['module'] = TEST_POLICY_MODULE
            instance = PolicyTypeAPI(**fixture)
            PolicyType.add_or_update(PolicyTypeAPI.to_model(instance))

        for _, fixture in six.iteritems(FIXTURES['policies']):
            instance = PolicyAPI(**fixture)
            Policy.add_or_update(PolicyAPI.to_model(instance))

    @mock.patch.object(
        ConcurrencyPolicy, 'apply',
        mock.MagicMock(side_effect=ConcurrencyPolicy(threshold=3).apply))
    def test_apply(self):
        liveaction = LiveActionDB(action='core.local', parameters={'cmd': 'uname -a'})
        liveaction, _ = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        ConcurrencyPolicy.apply.assert_called_once_with(liveaction)

    @mock.patch.object(ConcurrencyPolicy, 'get_threshold', mock.MagicMock(return_value=0))
    def test_enforce(self):
        liveaction = LiveActionDB(action='core.local', parameters={'cmd': 'uname -a'})
        liveaction, _ = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_CANCELED)
