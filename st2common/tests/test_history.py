import copy
import bson

from tests.fixtures import history as fixture
from st2tests import DbTestCase
from st2common.persistence.history import ActionExecutionHistory
from st2common.models.api.history import ActionExecutionHistoryAPI


class TestActionExecutionHistoryModel(DbTestCase):

    def setUp(self):
        super(TestActionExecutionHistoryModel, self).setUp()

        # Fake history record for action executions triggered by workflow runner.
        self.fake_history_subtasks = [
            {
                'id': str(bson.ObjectId()),
                'action': copy.deepcopy(fixture.ARTIFACTS['actions']['local']),
                'runner': copy.deepcopy(fixture.ARTIFACTS['runners']['run-local']),
                'execution': copy.deepcopy(fixture.ARTIFACTS['executions']['task1']),
            },
            {
                'id': str(bson.ObjectId()),
                'action': copy.deepcopy(fixture.ARTIFACTS['actions']['local']),
                'runner': copy.deepcopy(fixture.ARTIFACTS['runners']['run-local']),
                'execution': copy.deepcopy(fixture.ARTIFACTS['executions']['task2']),
            }
        ]

        # Fake history record for a workflow action execution triggered by rule.
        self.fake_history_workflow = {
            'id': str(bson.ObjectId()),
            'trigger': copy.deepcopy(fixture.ARTIFACTS['trigger']),
            'trigger_type': copy.deepcopy(fixture.ARTIFACTS['trigger_type']),
            'trigger_instance': copy.deepcopy(fixture.ARTIFACTS['trigger_instance']),
            'rule': copy.deepcopy(fixture.ARTIFACTS['rule']),
            'action': copy.deepcopy(fixture.ARTIFACTS['actions']['chain']),
            'runner': copy.deepcopy(fixture.ARTIFACTS['runners']['action-chain']),
            'execution': copy.deepcopy(fixture.ARTIFACTS['executions']['workflow']),
            'children': [task['id'] for task in self.fake_history_subtasks]
        }

    def test_model_complete(self):

        # Create API object.
        obj = ActionExecutionHistoryAPI(**copy.deepcopy(self.fake_history_workflow))
        self.assertDictEqual(obj.trigger, self.fake_history_workflow['trigger'])
        self.assertDictEqual(obj.trigger_type, self.fake_history_workflow['trigger_type'])
        self.assertDictEqual(obj.trigger_instance, self.fake_history_workflow['trigger_instance'])
        self.assertDictEqual(obj.rule, self.fake_history_workflow['rule'])
        self.assertDictEqual(obj.action, self.fake_history_workflow['action'])
        self.assertDictEqual(obj.runner, self.fake_history_workflow['runner'])
        self.assertDictEqual(obj.execution, self.fake_history_workflow['execution'])
        self.assertListEqual(obj.children, self.fake_history_workflow['children'])

        # Convert API object to DB model.
        model = ActionExecutionHistoryAPI.to_model(obj)
        self.assertEqual(str(model.id), obj.id)
        self.assertDictEqual(model.trigger, self.fake_history_workflow['trigger'])
        self.assertDictEqual(model.trigger_type, self.fake_history_workflow['trigger_type'])
        self.assertDictEqual(model.trigger_instance, self.fake_history_workflow['trigger_instance'])
        self.assertDictEqual(model.rule, self.fake_history_workflow['rule'])
        self.assertDictEqual(model.action, self.fake_history_workflow['action'])
        self.assertDictEqual(model.runner, self.fake_history_workflow['runner'])
        self.assertDictEqual(model.execution, self.fake_history_workflow['execution'])
        self.assertListEqual(model.children, self.fake_history_workflow['children'])

        # Convert DB model to API object.
        obj = ActionExecutionHistoryAPI.from_model(model)
        self.assertEqual(str(model.id), obj.id)
        self.assertDictEqual(obj.trigger, self.fake_history_workflow['trigger'])
        self.assertDictEqual(obj.trigger_type, self.fake_history_workflow['trigger_type'])
        self.assertDictEqual(obj.trigger_instance, self.fake_history_workflow['trigger_instance'])
        self.assertDictEqual(obj.rule, self.fake_history_workflow['rule'])
        self.assertDictEqual(obj.action, self.fake_history_workflow['action'])
        self.assertDictEqual(obj.runner, self.fake_history_workflow['runner'])
        self.assertDictEqual(obj.execution, self.fake_history_workflow['execution'])
        self.assertListEqual(obj.children, self.fake_history_workflow['children'])

    def test_crud_complete(self):
        # Create the DB record.
        obj = ActionExecutionHistoryAPI(**copy.deepcopy(self.fake_history_workflow))
        ActionExecutionHistory.add_or_update(ActionExecutionHistoryAPI.to_model(obj))
        model = ActionExecutionHistory.get_by_id(obj.id)
        self.assertEqual(str(model.id), obj.id)
        self.assertDictEqual(model.trigger, self.fake_history_workflow['trigger'])
        self.assertDictEqual(model.trigger_type, self.fake_history_workflow['trigger_type'])
        self.assertDictEqual(model.trigger_instance, self.fake_history_workflow['trigger_instance'])
        self.assertDictEqual(model.rule, self.fake_history_workflow['rule'])
        self.assertDictEqual(model.action, self.fake_history_workflow['action'])
        self.assertDictEqual(model.runner, self.fake_history_workflow['runner'])
        self.assertDictEqual(model.execution, self.fake_history_workflow['execution'])
        self.assertListEqual(model.children, self.fake_history_workflow['children'])

        # Update the DB record.
        children = [str(bson.ObjectId()), str(bson.ObjectId())]
        model.children = children
        ActionExecutionHistory.add_or_update(model)
        model = ActionExecutionHistory.get_by_id(obj.id)
        self.assertListEqual(model.children, children)

        # Delete the DB record.
        ActionExecutionHistory.delete(model)
        self.assertRaises(ValueError, ActionExecutionHistory.get_by_id, obj.id)

    def test_model_partial(self):
        # Create API object.
        obj = ActionExecutionHistoryAPI(**copy.deepcopy(self.fake_history_subtasks[0]))
        self.assertIsNone(getattr(obj, 'trigger', None))
        self.assertIsNone(getattr(obj, 'trigger_type', None))
        self.assertIsNone(getattr(obj, 'trigger_instance', None))
        self.assertIsNone(getattr(obj, 'rule', None))
        self.assertDictEqual(obj.action, self.fake_history_subtasks[0]['action'])
        self.assertDictEqual(obj.runner, self.fake_history_subtasks[0]['runner'])
        self.assertDictEqual(obj.execution, self.fake_history_subtasks[0]['execution'])
        self.assertIsNone(getattr(obj, 'children', None))

        # Convert API object to DB model.
        model = ActionExecutionHistoryAPI.to_model(obj)
        self.assertEqual(str(model.id), obj.id)
        self.assertDictEqual(model.trigger, {})
        self.assertDictEqual(model.trigger_type, {})
        self.assertDictEqual(model.trigger_instance, {})
        self.assertDictEqual(model.rule, {})
        self.assertDictEqual(model.action, self.fake_history_subtasks[0]['action'])
        self.assertDictEqual(model.runner, self.fake_history_subtasks[0]['runner'])
        self.assertDictEqual(model.execution, self.fake_history_subtasks[0]['execution'])
        self.assertListEqual(model.children, [])

        # Convert DB model to API object.
        obj = ActionExecutionHistoryAPI.from_model(model)
        self.assertEqual(str(model.id), obj.id)
        self.assertIsNone(getattr(obj, 'trigger', None))
        self.assertIsNone(getattr(obj, 'trigger_type', None))
        self.assertIsNone(getattr(obj, 'trigger_instance', None))
        self.assertIsNone(getattr(obj, 'rule', None))
        self.assertDictEqual(obj.action, self.fake_history_subtasks[0]['action'])
        self.assertDictEqual(obj.runner, self.fake_history_subtasks[0]['runner'])
        self.assertDictEqual(obj.execution, self.fake_history_subtasks[0]['execution'])
        self.assertIsNone(getattr(obj, 'children', None))

    def test_crud_partial(self):
        # Create the DB record.
        obj = ActionExecutionHistoryAPI(**copy.deepcopy(self.fake_history_subtasks[0]))
        ActionExecutionHistory.add_or_update(ActionExecutionHistoryAPI.to_model(obj))
        model = ActionExecutionHistory.get_by_id(obj.id)
        self.assertEqual(str(model.id), obj.id)
        self.assertDictEqual(model.trigger, {})
        self.assertDictEqual(model.trigger_type, {})
        self.assertDictEqual(model.trigger_instance, {})
        self.assertDictEqual(model.rule, {})
        self.assertDictEqual(model.action, self.fake_history_subtasks[0]['action'])
        self.assertDictEqual(model.runner, self.fake_history_subtasks[0]['runner'])
        self.assertDictEqual(model.execution, self.fake_history_subtasks[0]['execution'])
        self.assertListEqual(model.children, [])

        # Update the DB record.
        children = [str(bson.ObjectId()), str(bson.ObjectId())]
        model.children = children
        ActionExecutionHistory.add_or_update(model)
        model = ActionExecutionHistory.get_by_id(obj.id)
        self.assertListEqual(model.children, children)

        # Delete the DB record.
        ActionExecutionHistory.delete(model)
        self.assertRaises(ValueError, ActionExecutionHistory.get_by_id, obj.id)
