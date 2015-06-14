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

import datetime
import mock
import six

from st2tests import config as test_config
test_config.parse_args()

from oslo.config import cfg

from st2actions import scheduler
from st2common.constants import action as action_constants
from st2common.models.api.action import ActionAPI, RunnerTypeAPI
from st2common.models.db.action import LiveActionDB
from st2common.persistence.action import Action, LiveAction
from st2common.persistence.runner import RunnerType
from st2common.services import executions
from st2common.transport.liveaction import LiveActionPublisher
from st2common.transport.publishers import CUDPublisher
from st2common.util import date as date_utils
from st2tests import DbTestCase, fixturesloader
from tests.unit.base import MockLiveActionPublisher
from tests.unit.test_runner import TestRunner


TEST_FIXTURES = {
    'runners': [
        'testrunner1.yaml'
    ],
    'actions': [
        'action1.yaml'
    ]
}

PACK = 'generic'
LOADER = fixturesloader.FixturesLoader()
FIXTURES = LOADER.load_fixtures(fixtures_pack=PACK, fixtures_dict=TEST_FIXTURES)
NON_EMPTY_RESULT = 'non-empty'
RUN_RESULT = (action_constants.LIVEACTION_STATUS_SUCCEEDED, NON_EMPTY_RESULT, None)


@mock.patch.object(
    TestRunner, 'run',
    mock.MagicMock(return_value=RUN_RESULT))
@mock.patch.object(
    CUDPublisher, 'publish_update',
    mock.MagicMock(side_effect=MockLiveActionPublisher.publish_update))
@mock.patch.object(
    LiveActionPublisher, 'publish_state',
    mock.MagicMock(side_effect=MockLiveActionPublisher.publish_state))
class SchedulerTest(DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(SchedulerTest, cls).setUpClass()

        for _, fixture in six.iteritems(FIXTURES['runners']):
            instance = RunnerTypeAPI(**fixture)
            RunnerType.add_or_update(RunnerTypeAPI.to_model(instance))

        for _, fixture in six.iteritems(FIXTURES['actions']):
            instance = ActionAPI(**fixture)
            Action.add_or_update(ActionAPI.to_model(instance))

    def test_delayed_executions_recovery(self):
        # Create a live action that's already delayed pass the allowed timeout.
        dt_now = date_utils.get_datetime_utc_now()
        dt_delta = datetime.timedelta(seconds=cfg.CONF.scheduler.delayed_execution_recovery)
        dt_timeout = dt_now - dt_delta

        liveaction = LiveActionDB(action='wolfpack.action-1',
                                  parameters={'actionstr': 'foo'},
                                  start_timestamp=dt_timeout,
                                  status=action_constants.LIVEACTION_STATUS_DELAYED)

        liveaction = LiveAction.add_or_update(liveaction, publish=False)
        executions.create_execution_object(liveaction, publish=False)

        # Run the rescheduling routine.
        scheduler.recover_delayed_executions()

        # The live action is expected to complete.
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)

    def test_delayed_executions_recovery_before_timeout(self):
        # Create a live action that's delayed but has not passed the timeout.
        liveaction = LiveActionDB(action='wolfpack.action-1',
                                  parameters={'actionstr': 'foo'},
                                  start_timestamp=date_utils.get_datetime_utc_now(),
                                  status=action_constants.LIVEACTION_STATUS_DELAYED)

        liveaction = LiveAction.add_or_update(liveaction, publish=False)
        executions.create_execution_object(liveaction, publish=False)

        # Run the rescheduling routine.
        scheduler.recover_delayed_executions()

        # The live action is expected to stay "delayed".
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_DELAYED)
