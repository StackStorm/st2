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
import six

from st2common.constants import action as action_constants
from st2common.models.api.action import ActionAPI, RunnerTypeAPI
from st2common.models.api.policy import PolicyTypeAPI, PolicyAPI
from st2common.models.db.action import LiveActionDB
from st2common.persistence.action import Action, LiveAction
from st2common.persistence.policy import PolicyType, Policy
from st2common.persistence.runner import RunnerType
from st2common.services import action as action_service
from st2common.transport.liveaction import LiveActionPublisher
from st2common.transport.publishers import CUDPublisher
from st2tests import DbTestCase
from st2tests.fixturesloader import FixturesLoader
from st2tests.policies.concurrency import FakeConcurrencyApplicator
from st2tests.policies.mock_exception import RaiseExceptionApplicator
from tests.unit.base import MockLiveActionPublisher


TEST_FIXTURES = {
    'runners': [
        'testrunner1.yaml'
    ],
    'actions': [
        'action1.yaml'
    ],
    'policytypes': [
        'fake_policy_type_1.yaml',
        'fake_policy_type_2.yaml'
    ],
    'policies': [
        'policy_1.yaml',
        'policy_2.yaml'
    ]
}

PACK = 'generic'
LOADER = FixturesLoader()
FIXTURES = LOADER.load_fixtures(fixtures_pack=PACK, fixtures_dict=TEST_FIXTURES)


@mock.patch.object(
    CUDPublisher, 'publish_update',
    mock.MagicMock(side_effect=MockLiveActionPublisher.publish_update))
@mock.patch.object(
    CUDPublisher, 'publish_create',
    mock.MagicMock(return_value=None))
@mock.patch.object(
    LiveActionPublisher, 'publish_state',
    mock.MagicMock(side_effect=MockLiveActionPublisher.publish_state))
class SchedulingPolicyTest(DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(SchedulingPolicyTest, cls).setUpClass()

        for _, fixture in six.iteritems(FIXTURES['runners']):
            instance = RunnerTypeAPI(**fixture)
            RunnerType.add_or_update(RunnerTypeAPI.to_model(instance))

        for _, fixture in six.iteritems(FIXTURES['actions']):
            instance = ActionAPI(**fixture)
            Action.add_or_update(ActionAPI.to_model(instance))

        for _, fixture in six.iteritems(FIXTURES['policytypes']):
            instance = PolicyTypeAPI(**fixture)
            PolicyType.add_or_update(PolicyTypeAPI.to_model(instance))

        for _, fixture in six.iteritems(FIXTURES['policies']):
            instance = PolicyAPI(**fixture)
            Policy.add_or_update(PolicyAPI.to_model(instance))

    @mock.patch.object(
        FakeConcurrencyApplicator, 'apply_before',
        mock.MagicMock(
            side_effect=FakeConcurrencyApplicator(None, None, threshold=3).apply_before))
    @mock.patch.object(
        RaiseExceptionApplicator, 'apply_before',
        mock.MagicMock(
            side_effect=RaiseExceptionApplicator(None, None).apply_before))
    @mock.patch.object(
        FakeConcurrencyApplicator, 'apply_after',
        mock.MagicMock(
            side_effect=FakeConcurrencyApplicator(None, None, threshold=3).apply_after))
    @mock.patch.object(
        RaiseExceptionApplicator, 'apply_after',
        mock.MagicMock(
            side_effect=RaiseExceptionApplicator(None, None).apply_after))
    def test_apply(self):
        liveaction = LiveActionDB(action='wolfpack.action-1', parameters={'actionstr': 'foo'})
        liveaction, _ = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        FakeConcurrencyApplicator.apply_before.assert_called_once_with(liveaction)
        RaiseExceptionApplicator.apply_before.assert_called_once_with(liveaction)
        FakeConcurrencyApplicator.apply_after.assert_called_once_with(liveaction)
        RaiseExceptionApplicator.apply_after.assert_called_once_with(liveaction)

    @mock.patch.object(FakeConcurrencyApplicator, 'get_threshold', mock.MagicMock(return_value=0))
    def test_enforce(self):
        liveaction = LiveActionDB(action='wolfpack.action-1', parameters={'actionstr': 'foo'})
        liveaction, _ = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_CANCELED)
