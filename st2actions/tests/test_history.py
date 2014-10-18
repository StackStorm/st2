import copy

import mock

# XXX: actionsensor import depends on config being setup.
import st2tests.config as tests_config
tests_config.parse_args()

from tests.fixtures import history as fixture
from st2tests import DbTestCase
import st2actions.bootstrap.runnersregistrar as runners_registrar
from st2actions import worker, history
from st2actions.runners.fabricrunner import FabricRunner
from st2reactor.rules.enforcer import RuleEnforcer
from st2common.util import reference
from st2common.transport.publishers import CUDPublisher
from st2common.services import action as action_service
from st2common.models.db.action import ActionExecutionDB, ActionReference
from st2common.models.api.reactor import TriggerTypeAPI, TriggerAPI, TriggerInstanceAPI, RuleAPI
from st2common.models.api.action import RunnerTypeAPI, ActionAPI, ActionExecutionAPI
from st2common.models.api.action import ACTIONEXEC_STATUS_SUCCEEDED
import st2common.util.action_db as action_utils
from st2common.persistence.reactor import TriggerType, Trigger, TriggerInstance, Rule
from st2common.persistence.action import RunnerType, Action, ActionExecution
from st2common.persistence.history import ActionExecutionHistory


CHAMPION = worker.Worker(None)
HISTORIAN = history.Historian(None)


def process_create(payload):
    if isinstance(payload, ActionExecutionDB):
        HISTORIAN.record_action_execution(payload)
        CHAMPION.execute_action(payload)


def process_update(payload):
    if isinstance(payload, ActionExecutionDB):
        HISTORIAN.record_action_execution(payload)


@mock.patch.object(FabricRunner, '_run', mock.MagicMock(return_value={}))
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

    def test_basic_execution(self):
        action_ref = ActionReference(name='local', pack='core')
        execution = ActionExecutionDB(ref=action_ref.ref, parameters={'cmd': 'uname -a'})
        execution = action_service.schedule(execution)
        execution = ActionExecution.get_by_id(str(execution.id))
        self.assertEqual(execution.status, ACTIONEXEC_STATUS_SUCCEEDED)
        history = ActionExecutionHistory.get(execution__id=str(execution.id), raise_exception=True)
        self.assertDictEqual(history.trigger, {})
        self.assertDictEqual(history.trigger_type, {})
        self.assertDictEqual(history.trigger_instance, {})
        self.assertDictEqual(history.rule, {})
        action, _ = action_utils.get_action_by_dict({
            'name': action_ref.name, 'content_pack': action_ref.pack
            })
        self.assertDictEqual(history.action, vars(ActionAPI.from_model(action)))
        runner = RunnerType.get_by_name(action.runner_type['name'])
        self.assertDictEqual(history.runner, vars(RunnerTypeAPI.from_model(runner)))
        execution = ActionExecution.get_by_id(str(execution.id))
        self.assertDictEqual(history.execution, vars(ActionExecutionAPI.from_model(execution)))

    def test_chained_executions(self):
        action_ref = ActionReference(name='chain', pack='core')
        execution = ActionExecutionDB(ref=action_ref.ref)
        execution = action_service.schedule(execution)
        execution = ActionExecution.get_by_id(str(execution.id))
        self.assertEqual(execution.status, ACTIONEXEC_STATUS_SUCCEEDED)
        history = ActionExecutionHistory.get(execution__id=str(execution.id), raise_exception=True)
        action, _ = action_utils.get_action_by_dict({
            'name': action_ref.name, 'content_pack': action_ref.pack
            })
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
        rule.trigger = reference.get_ref_from_model(trigger)
        rule = Rule.add_or_update(rule)
        trigger_instance = TriggerInstance.add_or_update(
            TriggerInstanceAPI.to_model(TriggerInstanceAPI(**docs['trigger_instance'])))
        enforcer = RuleEnforcer(trigger_instance, rule)
        enforcer.enforce()

        # Wait for the action execution to complete and then confirm outcome.
        execution = ActionExecution.get(context__trigger_instance__id=str(trigger_instance.id))
        self.assertIsNotNone(execution)
        execution = ActionExecution.get_by_id(str(execution.id))
        self.assertEqual(execution.status, ACTIONEXEC_STATUS_SUCCEEDED)
        history = ActionExecutionHistory.get(execution__id=str(execution.id), raise_exception=True)
        self.assertDictEqual(history.trigger, vars(TriggerAPI.from_model(trigger)))
        self.assertDictEqual(history.trigger_type, vars(TriggerTypeAPI.from_model(trigger_type)))
        self.assertDictEqual(history.trigger_instance,
                             vars(TriggerInstanceAPI.from_model(trigger_instance)))
        self.assertDictEqual(history.rule, vars(RuleAPI.from_model(rule)))
        action_ref = ActionReference(ref=execution.ref)
        action, _ = action_utils.get_action_by_dict({
            'name': action_ref.name, 'content_pack': action_ref.pack
            })
        self.assertDictEqual(history.action, vars(ActionAPI.from_model(action)))
        runner = RunnerType.get_by_name(action.runner_type['name'])
        self.assertDictEqual(history.runner, vars(RunnerTypeAPI.from_model(runner)))
        execution = ActionExecution.get_by_id(str(execution.id))
        self.assertDictEqual(history.execution, vars(ActionExecutionAPI.from_model(execution)))
