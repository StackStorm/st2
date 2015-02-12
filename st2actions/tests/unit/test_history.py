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

from st2tests.fixtures import history as fixture
from st2tests import DbTestCase
import st2actions.bootstrap.runnersregistrar as runners_registrar
from st2actions import worker, history
from st2actions.runners.localrunner import LocalShellRunner
from st2reactor.rules.enforcer import RuleEnforcer
from st2common.util import reference
from st2common.transport.publishers import CUDPublisher
from st2common.services import action as action_service
from st2common.models.db.action import ActionExecutionDB
from st2common.models.api.reactor import TriggerTypeAPI, TriggerAPI, TriggerInstanceAPI
from st2common.models.api.rule import RuleAPI
from st2common.models.api.action import RunnerTypeAPI, ActionAPI, ActionExecutionAPI
import st2common.util.action_db as action_utils
from st2common.constants.action import ACTIONEXEC_STATUS_FAILED
from st2common.persistence.reactor import TriggerType, Trigger, TriggerInstance, Rule
from st2common.persistence.action import RunnerType, Action, ActionExecution
from st2common.persistence.history import ActionExecutionHistory


CHAMPION = worker.Worker(None)
HISTORIAN = history.Historian(None, timeout=1, wait=1)
MOCK_FAIL_HISTORY_CREATE = False


def process_create(payload):
    try:
        if isinstance(payload, ActionExecutionDB):
            if not MOCK_FAIL_HISTORY_CREATE:
                HISTORIAN.record_action_execution(payload)
            CHAMPION.execute_action(payload)
    except Exception as e:
        print(e)


def process_update(payload):
    try:
        if isinstance(payload, ActionExecutionDB):
            HISTORIAN.update_action_execution_history(payload)
    except Exception as e:
        print(e)


@mock.patch.object(LocalShellRunner, 'run', mock.MagicMock(return_value={}))
@mock.patch.object(CUDPublisher, 'publish_create', mock.MagicMock(side_effect=process_create))
@mock.patch.object(CUDPublisher, 'publish_update', mock.MagicMock(side_effect=process_update))
class TestActionExecutionHistoryWorker(DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestActionExecutionHistoryWorker, cls).setUpClass()
        runners_registrar.register_runner_types()
        action_local = ActionAPI(**copy.deepcopy(fixture.ARTIFACTS['actions']['local']))
        Action.add_or_update(ActionAPI.to_model(action_local))
        action_chain = ActionAPI(**copy.deepcopy(fixture.ARTIFACTS['actions']['chain']))
        action_chain.entry_point = fixture.PATH + '/chain.json'
        Action.add_or_update(ActionAPI.to_model(action_chain))

    def tearDown(self):
        MOCK_FAIL_HISTORY_CREATE = False    # noqa
        super(TestActionExecutionHistoryWorker, self).tearDown()

    def test_basic_execution(self):
        execution = ActionExecutionDB(action='core.local', parameters={'cmd': 'uname -a'})
        execution = action_service.schedule(execution)
        execution = ActionExecution.get_by_id(str(execution.id))
        self.assertEqual(execution.status, ACTIONEXEC_STATUS_FAILED)
        history = ActionExecutionHistory.get(execution__id=str(execution.id), raise_exception=True)
        self.assertDictEqual(history.trigger, {})
        self.assertDictEqual(history.trigger_type, {})
        self.assertDictEqual(history.trigger_instance, {})
        self.assertDictEqual(history.rule, {})
        action = action_utils.get_action_by_ref('core.local')
        self.assertDictEqual(history.action, vars(ActionAPI.from_model(action)))
        runner = RunnerType.get_by_name(action.runner_type['name'])
        self.assertDictEqual(history.runner, vars(RunnerTypeAPI.from_model(runner)))
        execution = ActionExecution.get_by_id(str(execution.id))
        self.assertDictEqual(history.execution, vars(ActionExecutionAPI.from_model(execution)))

    def test_basic_execution_history_create_failed(self):
        MOCK_FAIL_HISTORY_CREATE = True     # noqa
        self.test_basic_execution()

    def test_chained_executions(self):
        execution = ActionExecutionDB(action='core.chain')
        execution = action_service.schedule(execution)
        execution = ActionExecution.get_by_id(str(execution.id))
        self.assertEqual(execution.status, ACTIONEXEC_STATUS_FAILED)
        history = ActionExecutionHistory.get(execution__id=str(execution.id), raise_exception=True)
        action = action_utils.get_action_by_ref('core.chain')
        self.assertDictEqual(history.action, vars(ActionAPI.from_model(action)))
        runner = RunnerType.get_by_name(action.runner_type['name'])
        self.assertDictEqual(history.runner, vars(RunnerTypeAPI.from_model(runner)))
        execution = ActionExecution.get_by_id(str(execution.id))
        self.assertDictEqual(history.execution, vars(ActionExecutionAPI.from_model(execution)))
        self.assertGreater(len(history.children), 0)
        for child in history.children:
            record = ActionExecutionHistory.get(id=child, raise_exception=True)
            self.assertEqual(record.parent, str(history.id))
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
        enforcer = RuleEnforcer(trigger_instance, rule)
        enforcer.enforce()

        # Wait for the action execution to complete and then confirm outcome.
        execution = ActionExecution.get(context__trigger_instance__id=str(trigger_instance.id))
        self.assertIsNotNone(execution)
        execution = ActionExecution.get_by_id(str(execution.id))
        self.assertEqual(execution.status, ACTIONEXEC_STATUS_FAILED)
        history = ActionExecutionHistory.get(execution__id=str(execution.id), raise_exception=True)
        self.assertDictEqual(history.trigger, vars(TriggerAPI.from_model(trigger)))
        self.assertDictEqual(history.trigger_type, vars(TriggerTypeAPI.from_model(trigger_type)))
        self.assertDictEqual(history.trigger_instance,
                             vars(TriggerInstanceAPI.from_model(trigger_instance)))
        self.assertDictEqual(history.rule, vars(RuleAPI.from_model(rule)))
        action = action_utils.get_action_by_ref(execution.action)
        self.assertDictEqual(history.action, vars(ActionAPI.from_model(action)))
        runner = RunnerType.get_by_name(action.runner_type['name'])
        self.assertDictEqual(history.runner, vars(RunnerTypeAPI.from_model(runner)))
        execution = ActionExecution.get_by_id(str(execution.id))
        self.assertDictEqual(history.execution, vars(ActionExecutionAPI.from_model(execution)))
