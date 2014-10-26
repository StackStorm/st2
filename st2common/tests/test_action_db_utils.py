import copy
import datetime

import mock

from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.transport.publishers import PoolPublisher
from st2common.models.api.action import RunnerTypeAPI
from st2common.models.db.action import (ActionDB, ActionExecutionDB)
from st2common.models.system.common import ResourceReference
from st2common.persistence.action import (Action, ActionExecution, RunnerType)
import st2common.util.action_db as action_db_utils
from st2tests.base import DbTestCase


@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
class ActionDBUtilsTestCase(DbTestCase):
    runnertype_db = None
    action_db = None
    actionexec_db = None

    @classmethod
    def setUpClass(cls):
        super(ActionDBUtilsTestCase, cls).setUpClass()
        ActionDBUtilsTestCase._setup_test_models()

    def test_get_runnertype_nonexisting(self):
        # By id.
        self.assertRaises(StackStormDBObjectNotFoundError, action_db_utils.get_runnertype_by_id,
                          'somedummyrunnerid')
        # By name.
        self.assertRaises(StackStormDBObjectNotFoundError, action_db_utils.get_runnertype_by_name,
                          'somedummyrunnername')

    def test_get_runnertype_existing(self):
        # Lookup by id and verify name equals.
        runner = action_db_utils.get_runnertype_by_id(ActionDBUtilsTestCase.runnertype_db.id)
        self.assertEqual(runner.name, ActionDBUtilsTestCase.runnertype_db.name)
        # Lookup by name and verify id equals.
        runner = action_db_utils.get_runnertype_by_name(ActionDBUtilsTestCase.runnertype_db.name)
        self.assertEqual(runner.id, ActionDBUtilsTestCase.runnertype_db.id)

    def test_get_action_nonexisting(self):
        # By id.
        self.assertRaises(StackStormDBObjectNotFoundError, action_db_utils.get_action_by_id,
                          'somedummyactionid')
        # By ref.
        action = action_db_utils.get_action_by_ref('packaintexist.somedummyactionname')
        self.assertTrue(action is None)

    def test_get_action_existing(self):
        # Lookup by id and verify name equals
        action = action_db_utils.get_action_by_id(ActionDBUtilsTestCase.action_db.id)
        self.assertEqual(action.name, ActionDBUtilsTestCase.action_db.name)
        # Lookup by reference as string.
        action_ref = '.'.join([ActionDBUtilsTestCase.action_db.pack,
                               ActionDBUtilsTestCase.action_db.name])
        action = action_db_utils.get_action_by_ref(action_ref)
        self.assertEqual(action.id, ActionDBUtilsTestCase.action_db.id)
        # Lookup by action dict.
        # Dict contains name.
        lookup_action_dict = {
            'name': ActionDBUtilsTestCase.action_db.name,
            'pack': ActionDBUtilsTestCase.action_db.pack
        }
        action, _ = action_db_utils.get_action_by_dict(lookup_action_dict)
        self.assertEqual(action.id, ActionDBUtilsTestCase.action_db.id)
        # Dict contains both name + pack and id, id invalid.
        lookup_action_dict = {
            'name': ActionDBUtilsTestCase.action_db.name,
            'pack': ActionDBUtilsTestCase.action_db.pack,
            'id': 'haha'
        }
        action, _ = action_db_utils.get_action_by_dict(lookup_action_dict)
        self.assertTrue(action is not None)
        # Dict contains nothing.
        lookup_action_dict = {}
        action, _ = action_db_utils.get_action_by_dict(lookup_action_dict)
        self.assertTrue(action is None)

    def test_get_actionexec_nonexisting(self):
        # By id.
        self.assertRaises(StackStormDBObjectNotFoundError, action_db_utils.get_actionexec_by_id,
                          'somedummyactionexecid')

    def test_get_actionexec_existing(self):
        actionexec = action_db_utils.get_actionexec_by_id(ActionDBUtilsTestCase.actionexec_db.id)
        self.assertEqual(actionexec, ActionDBUtilsTestCase.actionexec_db)

    def test_update_actionexecution_status(self):
        actionexec_db = ActionExecutionDB()
        actionexec_db.status = 'initializing'
        actionexec_db.start_timestamp = datetime.datetime.utcnow()
        actionexec_db.action = ResourceReference(
            name=ActionDBUtilsTestCase.action_db.name,
            pack=ActionDBUtilsTestCase.action_db.pack).ref
        params = {
            'actionstr': 'foo',
            'some_key_that_aint_exist_in_action_or_runner': 'bar',
            'runnerint': 555
        }
        actionexec_db.parameters = params
        actionexec_db = ActionExecution.add_or_update(actionexec_db)
        origactionexec_db = copy.copy(actionexec_db)

        # Update by id.
        newactionexec_db = action_db_utils.update_actionexecution_status(
            'running', actionexec_id=actionexec_db.id)
        # Verify id didn't change.
        self.assertEqual(origactionexec_db.id, newactionexec_db.id)
        self.assertEqual(newactionexec_db.status, 'running')

    def test_update_actionexecution_status_invalid(self):
        actionexec_db = ActionExecutionDB()
        actionexec_db.status = 'initializing'
        actionexec_db.start_timestamp = datetime.datetime.utcnow()
        actionexec_db.action = ResourceReference(
            name=ActionDBUtilsTestCase.action_db.name,
            pack=ActionDBUtilsTestCase.action_db.pack).ref
        params = {
            'actionstr': 'foo',
            'some_key_that_aint_exist_in_action_or_runner': 'bar',
            'runnerint': 555
        }
        actionexec_db.parameters = params
        actionexec_db = ActionExecution.add_or_update(actionexec_db)

        # Update by id.
        self.assertRaises(ValueError, action_db_utils.update_actionexecution_status,
                          'mea culpa', actionexec_id=actionexec_db.id)

    def test_get_args(self):
        params = {
            'actionstr': 'foo',
            'actionint': 20,
            'runnerint': 555
        }
        pos_args, named_args = action_db_utils.get_args(params, ActionDBUtilsTestCase.action_db)
        self.assertEqual(pos_args, '20 foo', 'Positional args not parsed correctly.')
        self.assertTrue('actionint' not in named_args)
        self.assertTrue('actionstr' not in named_args)
        self.assertEqual(named_args.get('runnerint'), 555)

    @classmethod
    def _setup_test_models(cls):
        ActionDBUtilsTestCase.setup_runner()
        ActionDBUtilsTestCase.setup_action_models()

    @classmethod
    def setup_runner(cls):
        test_runner = {
            'name': 'test-runner',
            'description': 'A test runner.',
            'enabled': True,
            'runner_parameters': {
                'runnerstr': {
                    'description': 'Foo str param.',
                    'type': 'string',
                    'default': 'defaultfoo'
                },
                'runnerint': {
                    'description': 'Foo int param.',
                    'type': 'number'
                },
                'runnerdummy': {
                    'description': 'Dummy param.',
                    'type': 'string',
                    'default': 'runnerdummy'
                }
            },
            'runner_module': 'tests.test_runner'
        }
        runnertype_api = RunnerTypeAPI(**test_runner)
        ActionDBUtilsTestCase.runnertype_db = RunnerType.add_or_update(
            RunnerTypeAPI.to_model(runnertype_api))

    @classmethod
    @mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
    def setup_action_models(cls):
        action_db = ActionDB()
        action_db.name = 'action-1'
        action_db.description = 'awesomeness'
        action_db.enabled = True
        action_db.pack = 'wolfpack'
        action_db.entry_point = ''
        action_db.runner_type = {'name': 'test-runner'}
        action_db.parameters = {
            'actionstr': {'type': 'string', 'position': 1, 'required': True},
            'actionint': {'type': 'number', 'default': 10, 'position': 0},
            'runnerdummy': {'type': 'string', 'default': 'actiondummy'}
        }
        ActionDBUtilsTestCase.action_db = Action.add_or_update(action_db)

        actionexec_db = ActionExecutionDB()
        actionexec_db.status = 'initializing'
        actionexec_db.start_timestamp = datetime.datetime.utcnow()
        actionexec_db.action = ResourceReference(
            name=ActionDBUtilsTestCase.action_db.name,
            pack=ActionDBUtilsTestCase.action_db.pack).ref
        params = {
            'actionstr': 'foo',
            'some_key_that_aint_exist_in_action_or_runner': 'bar',
            'runnerint': 555
        }
        actionexec_db.parameters = params
        ActionDBUtilsTestCase.actionexec_db = ActionExecution.add_or_update(actionexec_db)
