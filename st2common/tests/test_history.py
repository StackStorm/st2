import copy
import json

from tests.data import fake
from st2tests import DbTestCase
from st2common.util import data as util
from st2common.persistence.history import ActionExecutionHistory
from st2common.models.api.history import ActionExecutionHistoryAPI


class TestActionExecutionHistoryModel(DbTestCase):

    def test_dot_notation_in_key(self):
        rule1 = json.loads(json.dumps(fake.RULE).replace('trigger.name', u'trigger\u2024name'))
        rule2 = util.replace_dot_in_key(copy.deepcopy(fake.RULE))
        rule3 = util.replace_u2024_in_key(copy.deepcopy(rule2))
        self.assertDictEqual(rule2, rule1)
        self.assertDictEqual(rule3, copy.deepcopy(fake.RULE))

    def test_model(self):
        # Create API object.
        obj = ActionExecutionHistoryAPI(**copy.deepcopy(fake.ACTION_EXECUTION_HISTORY))
        self.assertDictEqual(obj.trigger, fake.TRIGGER)
        self.assertDictEqual(obj.trigger_type, fake.TRIGGER_TYPE)
        self.assertDictEqual(obj.trigger_instance, fake.TRIGGER_INSTANCE)
        self.assertDictEqual(obj.rule, fake.RULE)
        self.assertDictEqual(obj.action, fake.ACTION)
        self.assertDictEqual(obj.runner_type, fake.RUNNER_TYPE)
        self.assertDictEqual(obj.execution, fake.ACTION_EXECUTION)

        # Convert API object to DB model.
        model = ActionExecutionHistoryAPI.to_model(obj)
        self.assertEqual(str(model.id), obj.id)
        self.assertDictEqual(model.trigger, fake.TRIGGER)
        self.assertDictEqual(model.trigger_type, fake.TRIGGER_TYPE)
        self.assertDictEqual(model.trigger_instance, fake.TRIGGER_INSTANCE)
        self.assertDictEqual(model.rule, util.replace_dot_in_key(copy.deepcopy(fake.RULE)))
        self.assertDictEqual(model.action, fake.ACTION)
        self.assertDictEqual(model.runner_type, fake.RUNNER_TYPE)
        self.assertDictEqual(model.execution, fake.ACTION_EXECUTION)

        # Convert DB model to API object.
        obj = ActionExecutionHistoryAPI.from_model(model)
        self.assertEqual(str(model.id), obj.id)
        self.assertDictEqual(obj.trigger, fake.TRIGGER)
        self.assertDictEqual(obj.trigger_type, fake.TRIGGER_TYPE)
        self.assertDictEqual(obj.trigger_instance, fake.TRIGGER_INSTANCE)
        self.assertDictEqual(obj.rule, fake.RULE)
        self.assertDictEqual(obj.action, fake.ACTION)
        self.assertDictEqual(obj.runner_type, fake.RUNNER_TYPE)
        self.assertDictEqual(obj.execution, fake.ACTION_EXECUTION)

    def test_crud(self):
        obj = ActionExecutionHistoryAPI(**copy.deepcopy(fake.ACTION_EXECUTION_HISTORY))
        model = ActionExecutionHistory.add_or_update(ActionExecutionHistoryAPI.to_model(obj))
        self.assertEqual(str(model.id), obj.id)
        self.assertDictEqual(model.trigger, fake.TRIGGER)
        self.assertDictEqual(model.trigger_type, fake.TRIGGER_TYPE)
        self.assertDictEqual(model.trigger_instance, fake.TRIGGER_INSTANCE)
        self.assertDictEqual(model.rule, util.replace_dot_in_key(copy.deepcopy(fake.RULE)))
        self.assertDictEqual(model.action, fake.ACTION)
        self.assertDictEqual(model.runner_type, fake.RUNNER_TYPE)
        self.assertDictEqual(model.execution, fake.ACTION_EXECUTION)
