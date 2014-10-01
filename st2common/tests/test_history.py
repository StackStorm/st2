import copy
import bson

from tests.fixtures import history as fixture
from st2tests import DbTestCase
from st2common.persistence.history import ActionExecutionHistory
from st2common.models.api.history import ActionExecutionHistoryAPI


class TestActionExecutionHistoryModel(DbTestCase):

    def setUp(self):
        super(TestActionExecutionHistoryModel, self).setUp()

        # Fake history record for an action execution triggered automatically by rule.
        self.fake_auto = {
            'id': str(bson.ObjectId()),
            'trigger': copy.deepcopy(fixture.ARTIFACTS['trigger']),
            'trigger_type': copy.deepcopy(fixture.ARTIFACTS['trigger_type']),
            'trigger_instance': copy.deepcopy(fixture.ARTIFACTS['trigger_instance']),
            'rule': copy.deepcopy(fixture.ARTIFACTS['rule']),
            'action': copy.deepcopy(fixture.ARTIFACTS['action']),
            'runner': copy.deepcopy(fixture.ARTIFACTS['runner']),
            'executions': copy.deepcopy(fixture.ARTIFACTS['executions'])
        }

        # Fake history record for an action execution triggered manually.
        self.fake_manual = {
            'id': str(bson.ObjectId()),
            'action': copy.deepcopy(fixture.ARTIFACTS['action']),
            'runner': copy.deepcopy(fixture.ARTIFACTS['runner']),
            'executions': copy.deepcopy(fixture.ARTIFACTS['executions'])
        }

    def test_model_complete(self):

        # Create API object.
        obj = ActionExecutionHistoryAPI(**copy.deepcopy(self.fake_auto))
        self.assertDictEqual(obj.trigger, self.fake_auto['trigger'])
        self.assertDictEqual(obj.trigger_type, self.fake_auto['trigger_type'])
        self.assertDictEqual(obj.trigger_instance, self.fake_auto['trigger_instance'])
        self.assertDictEqual(obj.rule, self.fake_auto['rule'])
        self.assertDictEqual(obj.action, self.fake_auto['action'])
        self.assertDictEqual(obj.runner, self.fake_auto['runner'])
        self.assertListEqual(obj.executions, self.fake_auto['executions'])

        # Convert API object to DB model.
        model = ActionExecutionHistoryAPI.to_model(obj)
        self.assertEqual(str(model.id), obj.id)
        self.assertDictEqual(model.trigger, self.fake_auto['trigger'])
        self.assertDictEqual(model.trigger_type, self.fake_auto['trigger_type'])
        self.assertDictEqual(model.trigger_instance, self.fake_auto['trigger_instance'])
        self.assertDictEqual(model.rule, self.fake_auto['rule'])
        self.assertDictEqual(model.action, self.fake_auto['action'])
        self.assertDictEqual(model.runner, self.fake_auto['runner'])
        self.assertListEqual(model.executions, self.fake_auto['executions'])

        # Convert DB model to API object.
        obj = ActionExecutionHistoryAPI.from_model(model)
        self.assertEqual(str(model.id), obj.id)
        self.assertDictEqual(obj.trigger, self.fake_auto['trigger'])
        self.assertDictEqual(obj.trigger_type, self.fake_auto['trigger_type'])
        self.assertDictEqual(obj.trigger_instance, self.fake_auto['trigger_instance'])
        self.assertDictEqual(obj.rule, self.fake_auto['rule'])
        self.assertDictEqual(obj.action, self.fake_auto['action'])
        self.assertDictEqual(obj.runner, self.fake_auto['runner'])
        self.assertListEqual(obj.executions, self.fake_auto['executions'])

    def test_crud_complete(self):
        obj = ActionExecutionHistoryAPI(**copy.deepcopy(self.fake_auto))
        model = ActionExecutionHistory.add_or_update(ActionExecutionHistoryAPI.to_model(obj))
        self.assertEqual(str(model.id), obj.id)
        self.assertDictEqual(model.trigger, self.fake_auto['trigger'])
        self.assertDictEqual(model.trigger_type, self.fake_auto['trigger_type'])
        self.assertDictEqual(model.trigger_instance, self.fake_auto['trigger_instance'])
        self.assertDictEqual(model.rule, self.fake_auto['rule'])
        self.assertDictEqual(model.action, self.fake_auto['action'])
        self.assertDictEqual(model.runner, self.fake_auto['runner'])
        self.assertListEqual(model.executions, self.fake_auto['executions'])

    def test_model_partial(self):
        # Create API object.
        obj = ActionExecutionHistoryAPI(**copy.deepcopy(self.fake_manual))
        self.assertIsNone(getattr(obj, 'trigger', None))
        self.assertIsNone(getattr(obj, 'trigger_type', None))
        self.assertIsNone(getattr(obj, 'trigger_instance', None))
        self.assertIsNone(getattr(obj, 'rule', None))
        self.assertDictEqual(obj.action, self.fake_auto['action'])
        self.assertDictEqual(obj.runner, self.fake_auto['runner'])
        self.assertListEqual(obj.executions, self.fake_auto['executions'])

        # Convert API object to DB model.
        model = ActionExecutionHistoryAPI.to_model(obj)
        self.assertEqual(str(model.id), obj.id)
        self.assertDictEqual(model.trigger, {})
        self.assertDictEqual(model.trigger_type, {})
        self.assertDictEqual(model.trigger_instance, {})
        self.assertDictEqual(model.rule, {})
        self.assertDictEqual(model.action, self.fake_auto['action'])
        self.assertDictEqual(model.runner, self.fake_auto['runner'])
        self.assertListEqual(model.executions, self.fake_auto['executions'])

        # Convert DB model to API object.
        obj = ActionExecutionHistoryAPI.from_model(model)
        self.assertEqual(str(model.id), obj.id)
        self.assertIsNone(getattr(obj, 'trigger', None))
        self.assertIsNone(getattr(obj, 'trigger_type', None))
        self.assertIsNone(getattr(obj, 'trigger_instance', None))
        self.assertIsNone(getattr(obj, 'rule', None))
        self.assertDictEqual(obj.action, self.fake_auto['action'])
        self.assertDictEqual(obj.runner, self.fake_auto['runner'])
        self.assertListEqual(obj.executions, self.fake_auto['executions'])

    def test_crud_partial(self):
        obj = ActionExecutionHistoryAPI(**copy.deepcopy(self.fake_manual))
        model = ActionExecutionHistory.add_or_update(ActionExecutionHistoryAPI.to_model(obj))
        self.assertEqual(str(model.id), obj.id)
        self.assertDictEqual(model.trigger, {})
        self.assertDictEqual(model.trigger_type, {})
        self.assertDictEqual(model.trigger_instance, {})
        self.assertDictEqual(model.rule, {})
        self.assertDictEqual(model.action, self.fake_auto['action'])
        self.assertDictEqual(model.runner, self.fake_auto['runner'])
        self.assertListEqual(model.executions, self.fake_auto['executions'])
