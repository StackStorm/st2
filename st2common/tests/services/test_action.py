import mock
import jsonschema

from st2tests import DbTestCase
from st2common.util import isotime
from st2common.transport.publishers import PoolPublisher
from st2common.services import action as action_service
from st2common.persistence.action import RunnerType, Action, ActionExecution
from st2common.models.db.action import ActionExecutionDB, ActionCompoundKey
from st2common.models.api.action import RunnerTypeAPI, ActionAPI
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

ACTION_REF = ActionCompoundKey(name='my.action', content_pack='default')
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
        request = ActionExecutionDB(action=ACTION_REF, context=context, parameters=parameters)
        request = action_service.schedule(request)
        execution = ActionExecution.get_by_id(str(request.id))
        self.assertIsNotNone(execution)
        self.assertEqual(execution.id, request.id)
        action = {'name': self.actiondb.name,
                  'content_pack': self.actiondb.content_pack}
        actual_action = {'name': execution.action.name,
                         'content_pack': execution.action.content_pack}
        self.assertDictEqual(actual_action, action)
        self.assertEqual(execution.context['user'], request.context['user'])
        self.assertDictEqual(execution.parameters, request.parameters)
        self.assertEqual(execution.status, ACTIONEXEC_STATUS_SCHEDULED)
        # mongoengine DateTimeField stores datetime only up to milliseconds
        self.assertEqual(isotime.format(execution.start_timestamp, usec=False),
                         isotime.format(request.start_timestamp, usec=False))

    def test_schedule_invalid_parameters(self):
        parameters = {'hosts': 'localhost', 'cmd': 'uname -a', 'a': 123}
        execution = ActionExecutionDB(action=ACTION_REF, parameters=parameters)
        self.assertRaises(jsonschema.ValidationError, action_service.schedule, execution)

    def test_schedule_nonexistent_action(self):
        parameters = {'hosts': 'localhost', 'cmd': 'uname -a'}
        action_key = ActionCompoundKey(name='i.action', content_pack='default')
        execution = ActionExecutionDB(action=action_key, parameters=parameters)
        self.assertRaises(ValueError, action_service.schedule, execution)

    def test_schedule_disabled_action(self):
        self.actiondb.enabled = False
        Action.add_or_update(self.actiondb)
        parameters = {'hosts': 'localhost', 'cmd': 'uname -a'}
        execution = ActionExecutionDB(action=ACTION_REF, parameters=parameters)
        self.assertRaises(ValueError, action_service.schedule, execution)
        self.actiondb.enabled = True
        Action.add_or_update(self.actiondb)
