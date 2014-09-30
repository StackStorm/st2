import copy
import json
import bson

from tests.fixtures import history as fixture
from st2tests import DbTestCase
from st2common.util import mongoescape as util
from st2common.persistence.history import ActionExecutionHistory
from st2common.models.api.history import ActionExecutionHistoryAPI


class TestActionExecutionHistoryModel(DbTestCase):

    def setUp(self):
        super(TestActionExecutionHistoryModel, self).setUp()
        self.fake_history = {
            'id': str(bson.ObjectId()),
            'trigger': copy.deepcopy(fixture.ARTIFACTS['trigger']),
            'trigger_type': copy.deepcopy(fixture.ARTIFACTS['trigger_type']),
            'trigger_instance': copy.deepcopy(fixture.ARTIFACTS['trigger_instance']),
            'rule': copy.deepcopy(fixture.ARTIFACTS['rule']),
            'action': copy.deepcopy(fixture.ARTIFACTS['action']),
            'runner_type': copy.deepcopy(fixture.ARTIFACTS['runner_type']),
            'execution': copy.deepcopy(fixture.ARTIFACTS['executions'][0])
        }

    def test_dot_notation_in_key(self):
        original = self.fake_history['rule']
        escaped = json.loads(json.dumps(original).replace('trigger.name', u'trigger\uff0ename'))
        rule1 = util.escape_chars(copy.deepcopy(original))
        rule2 = util.unescape_chars(copy.deepcopy(rule1))
        self.assertDictEqual(rule1, escaped)
        self.assertDictEqual(rule2, original)

    def test_model(self):
        # Create API object.
        obj = ActionExecutionHistoryAPI(**copy.deepcopy(self.fake_history))
        self.assertDictEqual(obj.trigger, self.fake_history['trigger'])
        self.assertDictEqual(obj.trigger_type, self.fake_history['trigger_type'])
        self.assertDictEqual(obj.trigger_instance, self.fake_history['trigger_instance'])
        self.assertDictEqual(obj.rule, self.fake_history['rule'])
        self.assertDictEqual(obj.action, self.fake_history['action'])
        self.assertDictEqual(obj.runner_type, self.fake_history['runner_type'])
        self.assertDictEqual(obj.execution, self.fake_history['execution'])

        # Convert API object to DB model.
        model = ActionExecutionHistoryAPI.to_model(obj)
        self.assertEqual(str(model.id), obj.id)
        self.assertDictEqual(model.trigger, self.fake_history['trigger'])
        self.assertDictEqual(model.trigger_type, self.fake_history['trigger_type'])
        self.assertDictEqual(model.trigger_instance, self.fake_history['trigger_instance'])
        escaped_rule = util.escape_chars(copy.deepcopy(self.fake_history['rule']))
        self.assertDictEqual(model.rule, escaped_rule)
        self.assertDictEqual(model.action, self.fake_history['action'])
        self.assertDictEqual(model.runner_type, self.fake_history['runner_type'])
        self.assertDictEqual(model.execution, self.fake_history['execution'])

        # Convert DB model to API object.
        obj = ActionExecutionHistoryAPI.from_model(model)
        self.assertEqual(str(model.id), obj.id)
        self.assertDictEqual(obj.trigger, self.fake_history['trigger'])
        self.assertDictEqual(obj.trigger_type, self.fake_history['trigger_type'])
        self.assertDictEqual(obj.trigger_instance, self.fake_history['trigger_instance'])
        self.assertDictEqual(obj.rule, self.fake_history['rule'])
        self.assertDictEqual(obj.action, self.fake_history['action'])
        self.assertDictEqual(obj.runner_type, self.fake_history['runner_type'])
        self.assertDictEqual(obj.execution, self.fake_history['execution'])

    def test_crud(self):
        obj = ActionExecutionHistoryAPI(**copy.deepcopy(self.fake_history))
        model = ActionExecutionHistory.add_or_update(ActionExecutionHistoryAPI.to_model(obj))
        self.assertEqual(str(model.id), obj.id)
        self.assertDictEqual(model.trigger, self.fake_history['trigger'])
        self.assertDictEqual(model.trigger_type, self.fake_history['trigger_type'])
        self.assertDictEqual(model.trigger_instance, self.fake_history['trigger_instance'])
        escaped_rule = util.escape_chars(copy.deepcopy(self.fake_history['rule']))
        self.assertDictEqual(model.rule, escaped_rule)
        self.assertDictEqual(model.action, self.fake_history['action'])
        self.assertDictEqual(model.runner_type, self.fake_history['runner_type'])
        self.assertDictEqual(model.execution, self.fake_history['execution'])
