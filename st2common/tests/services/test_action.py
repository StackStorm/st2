import datetime

import bson
import mock
import jsonschema

from st2tests import DbTestCase
from st2common.transport.publishers import PoolPublisher
from st2common.services import action as action_service
from st2common.persistence.action import RunnerType, Action, ActionExecution
from st2common.models.api.action import RunnerTypeAPI, ActionAPI, ActionExecutionAPI
from st2common.models.api.action import ACTIONEXEC_STATUS_SCHEDULED


RUNNER = {
    'name': 'run-local',
    'description': 'A runner to execute local command.',
    'enabled': True,
    'runner_parameters': {
        'hosts': {'type': 'string'},
        'cmd': {'type': 'string'}
    },
    'runner_module': 'st2actions.runners.fabricrunner'
}

ACTION = {
    'name': 'my.action',
    'description': 'my test',
    'enabled': True,
    'entry_point': '/tmp/test/action.sh',
    'content_pack': 'default',
    'runner_type': 'run-local',
    'parameters': {
        'a': {
            'type': 'string',
            'default': 'abc'
        }
    }
}

ACTION_REF = {'name': 'my.action'}
USERNAME = 'stanley'


@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
class TestActionExecutionService(DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestActionExecutionService, cls).setUpClass()
        cls.runner = RunnerTypeAPI(**RUNNER)
        cls.runnerdb = RunnerType.add_or_update(RunnerTypeAPI.to_model(cls.runner))
        cls.action = ActionAPI(**ACTION)
        cls.actiondb = Action.add_or_update(ActionAPI.to_model(cls.action))

    @classmethod
    def tearDownClass(cls):
        Action.delete(cls.actiondb)
        RunnerType.delete(cls.runnerdb)
        super(TestActionExecutionService, cls).tearDownClass()

    def test_schedule(self):
        context = {'user': USERNAME}
        parameters = {'hosts': 'localhost', 'cmd': 'uname -a'}
        execution = ActionExecutionAPI(action=ACTION_REF, context=context, parameters=parameters)
        execution = action_service.schedule(execution)
        self.assertIsNotNone(execution)
        self.assertIsNotNone(execution.id)
        self.assertEqual(execution.context['user'], USERNAME)
        self.assertEqual(execution.status, ACTIONEXEC_STATUS_SCHEDULED)
        self.assertIsInstance(execution.start_timestamp, datetime.datetime)
        executiondb = ActionExecution.get_by_id(execution.id)
        self.assertIsNotNone(executiondb)
        self.assertEqual(executiondb.id, bson.ObjectId(execution.id))
        action = {'id': str(self.actiondb.id), 'name': self.actiondb.name}
        self.assertDictEqual(executiondb.action, action)
        self.assertEqual(executiondb.context['user'], execution.context['user'])
        self.assertDictEqual(executiondb.parameters, execution.parameters)
        self.assertEqual(executiondb.status, ACTIONEXEC_STATUS_SCHEDULED)
        self.assertIsInstance(executiondb.start_timestamp, datetime.datetime)

    def test_schedule_invalid_parameters(self):
        parameters = {'hosts': 'localhost', 'cmd': 'uname -a', 'a': 123}
        execution = ActionExecutionAPI(action=ACTION_REF, parameters=parameters)
        self.assertRaises(jsonschema.ValidationError, action_service.schedule, execution)

    def test_schedule_nonexistent_action(self):
        parameters = {'hosts': 'localhost', 'cmd': 'uname -a'}
        execution = ActionExecutionAPI(action={'name': 'i.action'}, parameters=parameters)
        self.assertRaises(ValueError, action_service.schedule, execution)

    def test_schedule_disabled_action(self):
        self.actiondb.enabled = False
        Action.add_or_update(self.actiondb)
        parameters = {'hosts': 'localhost', 'cmd': 'uname -a'}
        execution = ActionExecutionAPI(action=ACTION_REF, parameters=parameters)
        self.assertRaises(ValueError, action_service.schedule, execution)
        self.actiondb.enabled = True
        Action.add_or_update(self.actiondb)
