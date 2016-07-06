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

# XXX: actionsensor import depends on config being setup.
import st2tests.config as tests_config
tests_config.parse_args()

import st2common.bootstrap.runnersregistrar as runners_registrar
from st2actions.runners.localrunner import LocalShellRunner
from st2common.constants import action as action_constants
from st2common.models.db.liveaction import LiveActionDB
from st2common.models.api.trigger import TriggerTypeAPI, TriggerAPI, TriggerInstanceAPI
from st2common.models.api.rule import RuleAPI
from st2common.models.api.action import RunnerTypeAPI, ActionAPI
from st2common.persistence.action import Action
from st2common.persistence.execution import ActionExecution
from st2common.persistence.liveaction import LiveAction
from st2common.persistence.rule import Rule
from st2common.persistence.runner import RunnerType
from st2common.persistence.trigger import TriggerType, Trigger, TriggerInstance
from st2common.services import action as action_service
from st2common.services import trace as trace_service
from st2common.transport.liveaction import LiveActionPublisher
from st2common.transport.publishers import CUDPublisher
import st2common.util.action_db as action_utils
from st2common.util import reference
from st2reactor.rules.enforcer import RuleEnforcer
from st2tests.fixtures.packs import executions as fixture
from st2tests import DbTestCase
from tests.unit.base import MockLiveActionPublisher


MOCK_FAIL_EXECUTION_CREATE = False


@mock.patch.object(LocalShellRunner, 'run',
                   mock.MagicMock(return_value=(action_constants.LIVEACTION_STATUS_FAILED,
                                                'Non-empty', None)))
@mock.patch.object(CUDPublisher, 'publish_create',
                   mock.MagicMock(side_effect=MockLiveActionPublisher.publish_create))
@mock.patch.object(LiveActionPublisher, 'publish_state',
                   mock.MagicMock(side_effect=MockLiveActionPublisher.publish_state))
class TestActionExecutionHistoryWorker(DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestActionExecutionHistoryWorker, cls).setUpClass()
        runners_registrar.register_runner_types()
        action_local = ActionAPI(**copy.deepcopy(fixture.ARTIFACTS['actions']['local']))
        Action.add_or_update(ActionAPI.to_model(action_local))
        action_chain = ActionAPI(**copy.deepcopy(fixture.ARTIFACTS['actions']['chain']))
        action_chain.entry_point = fixture.PATH + '/chain.yaml'
        Action.add_or_update(ActionAPI.to_model(action_chain))

    def tearDown(self):
        MOCK_FAIL_EXECUTION_CREATE = False      # noqa
        super(TestActionExecutionHistoryWorker, self).tearDown()

    def test_basic_execution(self):
        liveaction = LiveActionDB(action='executions.local', parameters={'cmd': 'uname -a'})
        liveaction, _ = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_FAILED)
        execution = self._get_action_execution(liveaction__id=str(liveaction.id),
                                               raise_exception=True)
        self.assertDictEqual(execution.trigger, {})
        self.assertDictEqual(execution.trigger_type, {})
        self.assertDictEqual(execution.trigger_instance, {})
        self.assertDictEqual(execution.rule, {})
        action = action_utils.get_action_by_ref('executions.local')
        self.assertDictEqual(execution.action, vars(ActionAPI.from_model(action)))
        runner = RunnerType.get_by_name(action.runner_type['name'])
        self.assertDictEqual(execution.runner, vars(RunnerTypeAPI.from_model(runner)))
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(execution.start_timestamp, liveaction.start_timestamp)
        self.assertEqual(execution.end_timestamp, liveaction.end_timestamp)
        self.assertEqual(execution.result, liveaction.result)
        self.assertEqual(execution.status, liveaction.status)
        self.assertEqual(execution.context, liveaction.context)
        self.assertEqual(execution.liveaction['callback'], liveaction.callback)
        self.assertEqual(execution.liveaction['action'], liveaction.action)

    def test_basic_execution_history_create_failed(self):
        MOCK_FAIL_EXECUTION_CREATE = True     # noqa
        self.test_basic_execution()

    def test_chained_executions(self):
        liveaction = LiveActionDB(action='executions.chain')
        liveaction, _ = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_FAILED)
        execution = self._get_action_execution(liveaction__id=str(liveaction.id),
                                               raise_exception=True)
        action = action_utils.get_action_by_ref('executions.chain')
        self.assertDictEqual(execution.action, vars(ActionAPI.from_model(action)))
        runner = RunnerType.get_by_name(action.runner_type['name'])
        self.assertDictEqual(execution.runner, vars(RunnerTypeAPI.from_model(runner)))
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(execution.start_timestamp, liveaction.start_timestamp)
        self.assertEqual(execution.end_timestamp, liveaction.end_timestamp)
        self.assertEqual(execution.result, liveaction.result)
        self.assertEqual(execution.status, liveaction.status)
        self.assertEqual(execution.context, liveaction.context)
        self.assertEqual(execution.liveaction['callback'], liveaction.callback)
        self.assertEqual(execution.liveaction['action'], liveaction.action)
        self.assertGreater(len(execution.children), 0)
        for child in execution.children:
            record = ActionExecution.get(id=child, raise_exception=True)
            self.assertEqual(record.parent, str(execution.id))
            self.assertEqual(record.action['name'], 'local')
            self.assertEqual(record.runner['name'], 'run-local')

    def test_triggered_execution(self):
        docs = {
            'trigger_type': copy.deepcopy(fixture.ARTIFACTS['trigger_type']),
            'trigger': copy.deepcopy(fixture.ARTIFACTS['trigger']),
            'rule': copy.deepcopy(fixture.ARTIFACTS['rule']),
            'trigger_instance': copy.deepcopy(fixture.ARTIFACTS['trigger_instance'])}

        # Trigger an action execution.
        trigger_type = TriggerType.add_or_update(
            TriggerTypeAPI.to_model(TriggerTypeAPI(**docs['trigger_type'])))
        trigger = Trigger.add_or_update(TriggerAPI.to_model(TriggerAPI(**docs['trigger'])))
        rule = RuleAPI.to_model(RuleAPI(**docs['rule']))
        rule.trigger = reference.get_str_resource_ref_from_model(trigger)
        rule = Rule.add_or_update(rule)
        trigger_instance = TriggerInstance.add_or_update(
            TriggerInstanceAPI.to_model(TriggerInstanceAPI(**docs['trigger_instance'])))
        trace_service.add_or_update_given_trace_context(
            trace_context={'trace_tag': 'test_triggered_execution_trace'},
            trigger_instances=[str(trigger_instance.id)])
        enforcer = RuleEnforcer(trigger_instance, rule)
        enforcer.enforce()

        # Wait for the action execution to complete and then confirm outcome.
        liveaction = LiveAction.get(context__trigger_instance__id=str(trigger_instance.id))
        self.assertIsNotNone(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_FAILED)
        execution = self._get_action_execution(liveaction__id=str(liveaction.id),
                                               raise_exception=True)
        self.assertDictEqual(execution.trigger, vars(TriggerAPI.from_model(trigger)))
        self.assertDictEqual(execution.trigger_type, vars(TriggerTypeAPI.from_model(trigger_type)))
        self.assertDictEqual(execution.trigger_instance,
                             vars(TriggerInstanceAPI.from_model(trigger_instance)))
        self.assertDictEqual(execution.rule, vars(RuleAPI.from_model(rule)))
        action = action_utils.get_action_by_ref(liveaction.action)
        self.assertDictEqual(execution.action, vars(ActionAPI.from_model(action)))
        runner = RunnerType.get_by_name(action.runner_type['name'])
        self.assertDictEqual(execution.runner, vars(RunnerTypeAPI.from_model(runner)))
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(execution.start_timestamp, liveaction.start_timestamp)
        self.assertEqual(execution.end_timestamp, liveaction.end_timestamp)
        self.assertEqual(execution.result, liveaction.result)
        self.assertEqual(execution.status, liveaction.status)
        self.assertEqual(execution.context, liveaction.context)
        self.assertEqual(execution.liveaction['callback'], liveaction.callback)
        self.assertEqual(execution.liveaction['action'], liveaction.action)

    def _get_action_execution(self, **kwargs):
        return ActionExecution.get(**kwargs)
