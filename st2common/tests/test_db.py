import datetime
import jsonschema
import mock
import mongoengine.connection
from oslo.config import cfg
from st2common.transport.publishers import PoolPublisher
from st2common.util import schema as util_schema
from st2common.util import reference
from st2tests import DbTestCase

SKIP_DELETE = False
DUMMY_DESCRIPTION = 'Sample Description.'


class DbConnectionTest(DbTestCase):

    def test_check_connect(self):
        """
        Tests connectivity to the db server. Requires the db server to be
        running.
        """
        client = mongoengine.connection.get_connection()
        self.assertEqual(client.host, cfg.CONF.database.host,
                         'Not connected to desired host.')
        self.assertEqual(client.port, cfg.CONF.database.port,
                         'Not connected to desired port.')


from st2common.models.db.reactor import TriggerTypeDB, TriggerDB, TriggerInstanceDB, \
    RuleEnforcementDB, RuleDB, ActionExecutionSpecDB
from st2common.persistence.reactor import TriggerType, Trigger, TriggerInstance, \
    RuleEnforcement, Rule


@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
class ReactorModelTest(DbTestCase):

    def test_triggertype_crud(self):
        saved = ReactorModelTest._create_save_triggertype()
        retrieved = TriggerType.get_by_id(saved.id)
        self.assertEqual(saved.name, retrieved.name,
                         'Same triggertype was not returned.')
        # test update
        self.assertEqual(retrieved.description, '')
        retrieved.description = DUMMY_DESCRIPTION
        saved = TriggerType.add_or_update(retrieved)
        retrieved = TriggerType.get_by_id(saved.id)
        self.assertEqual(retrieved.description, DUMMY_DESCRIPTION, 'Update to trigger failed.')
        # cleanup
        ReactorModelTest._delete([retrieved])
        try:
            retrieved = TriggerType.get_by_id(saved.id)
        except ValueError:
            retrieved = None
        self.assertIsNone(retrieved, 'managed to retrieve after failure.')

    def test_trigger_crud(self):
        triggertype = ReactorModelTest._create_save_triggertype()
        saved = ReactorModelTest._create_save_trigger(triggertype)
        retrieved = Trigger.get_by_id(saved.id)
        self.assertEqual(saved.name, retrieved.name,
                         'Same trigger was not returned.')
        # test update
        self.assertEqual(retrieved.description, '')
        retrieved.description = DUMMY_DESCRIPTION
        saved = Trigger.add_or_update(retrieved)
        retrieved = Trigger.get_by_id(saved.id)
        self.assertEqual(retrieved.description, DUMMY_DESCRIPTION, 'Update to trigger failed.')
        # cleanup
        ReactorModelTest._delete([retrieved, triggertype])
        try:
            retrieved = Trigger.get_by_id(saved.id)
        except ValueError:
            retrieved = None
        self.assertIsNone(retrieved, 'managed to retrieve after failure.')

    def test_triggerinstance_crud(self):
        triggertype = ReactorModelTest._create_save_triggertype()
        trigger = ReactorModelTest._create_save_trigger(triggertype)
        saved = ReactorModelTest._create_save_triggerinstance(trigger)
        retrieved = TriggerInstance.get_by_id(saved.id)
        self.assertIsNotNone(retrieved, 'No triggerinstance created.')
        ReactorModelTest._delete([retrieved, trigger, triggertype])
        try:
            retrieved = TriggerInstance.get_by_id(saved.id)
        except ValueError:
            retrieved = None
        self.assertIsNone(retrieved, 'managed to retrieve after failure.')

    def test_rule_crud(self):
        triggertype = ReactorModelTest._create_save_triggertype()
        trigger = ReactorModelTest._create_save_trigger(triggertype)
        runnertype = ActionModelTest._create_save_runnertype()
        action = ActionModelTest._create_save_action(runnertype)
        saved = ReactorModelTest._create_save_rule(trigger, action)
        retrieved = Rule.get_by_id(saved.id)
        self.assertEqual(saved.name, retrieved.name, 'Same rule was not returned.')
        # test update
        self.assertEqual(retrieved.enabled, True)
        retrieved.enabled = False
        saved = Rule.add_or_update(retrieved)
        retrieved = Rule.get_by_id(saved.id)
        self.assertEqual(retrieved.enabled, False, 'Update to rule failed.')
        # cleanup
        ReactorModelTest._delete([retrieved, trigger, action, runnertype, triggertype])
        try:
            retrieved = Rule.get_by_id(saved.id)
        except ValueError:
            retrieved = None
        self.assertIsNone(retrieved, 'managed to retrieve after failure.')

    def test_ruleenforcement_crud(self):
        triggertype = ReactorModelTest._create_save_triggertype()
        trigger = ReactorModelTest._create_save_trigger(triggertype)
        runnertype = ActionModelTest._create_save_runnertype()
        action = ActionModelTest._create_save_action(runnertype)
        triggerinstance = ReactorModelTest._create_save_triggerinstance(trigger)
        rule = ReactorModelTest._create_save_rule(trigger, action)
        saved = ReactorModelTest._create_save_ruleenforcement(triggerinstance,
                                                              rule)
        retrieved = RuleEnforcement.get_by_id(saved.id)
        self.assertIsNotNone(retrieved, 'No ruleenforcement created.')
        ReactorModelTest._delete([retrieved, rule, triggerinstance, trigger,
                                  action, runnertype, triggertype])
        try:
            retrieved = RuleEnforcement.get_by_id(saved.id)
        except ValueError:
            retrieved = None
        self.assertIsNone(retrieved, 'managed to retrieve after failure.')

    def test_rule_lookup(self):
        triggertype = ReactorModelTest._create_save_triggertype()
        trigger = ReactorModelTest._create_save_trigger(triggertype)
        runnertype = ActionModelTest._create_save_runnertype()
        action = ActionModelTest._create_save_action(runnertype)
        saved = ReactorModelTest._create_save_rule(trigger, action)
        retrievedrules = Rule.query(trigger=reference.get_ref_from_model(trigger))
        self.assertEqual(1, len(retrievedrules), 'No rules found.')
        for retrievedrule in retrievedrules:
            self.assertEqual(saved.id, retrievedrule.id, 'Incorrect rule returned.')
        ReactorModelTest._delete([saved, trigger, action, runnertype, triggertype])

    def test_rule_lookup_enabled(self):
        triggertype = ReactorModelTest._create_save_triggertype()
        trigger = ReactorModelTest._create_save_trigger(triggertype)
        runnertype = ActionModelTest._create_save_runnertype()
        action = ActionModelTest._create_save_action(runnertype)
        saved = ReactorModelTest._create_save_rule(trigger, action)
        retrievedrules = Rule.query(trigger=reference.get_ref_from_model(trigger),
                                    enabled=True)
        self.assertEqual(1, len(retrievedrules), 'Error looking up enabled rules.')
        for retrievedrule in retrievedrules:
            self.assertEqual(saved.id, retrievedrule.id,
                             'Incorrect rule returned.')
        ReactorModelTest._delete([saved, trigger, action, runnertype, triggertype])

    def test_rule_lookup_disabled(self):
        triggertype = ReactorModelTest._create_save_triggertype()
        trigger = ReactorModelTest._create_save_trigger(triggertype)
        runnertype = ActionModelTest._create_save_runnertype()
        action = ActionModelTest._create_save_action(runnertype)
        saved = ReactorModelTest._create_save_rule(trigger, action, False)
        retrievedrules = Rule.query(trigger=reference.get_ref_from_model(trigger),
                                    enabled=False)
        self.assertEqual(1, len(retrievedrules), 'Error looking up enabled rules.')
        for retrievedrule in retrievedrules:
            self.assertEqual(saved.id, retrievedrule.id, 'Incorrect rule returned.')
        ReactorModelTest._delete([saved, trigger, action, runnertype, triggertype])

    def test_trigger_lookup(self):
        triggertype = ReactorModelTest._create_save_triggertype()
        saved = ReactorModelTest._create_save_trigger(triggertype)
        retrievedtriggers = Trigger.query(name=saved.name)
        self.assertEqual(1, len(retrievedtriggers), 'No triggers found.')
        for retrievedtrigger in retrievedtriggers:
            self.assertEqual(saved.id, retrievedtrigger.id,
                             'Incorrect trigger returned.')
        ReactorModelTest._delete([saved, triggertype])

    @staticmethod
    def _create_save_triggertype():
        created = TriggerTypeDB()
        created.content_pack = 'dummy_pack_1'
        created.name = 'triggertype-1'
        created.description = ''
        created.payload_schema = {}
        created.parameters_schema = {}
        return Trigger.add_or_update(created)

    @staticmethod
    def _create_save_trigger(triggertype):
        created = TriggerDB()
        created.name = 'trigger-1'
        created.description = ''
        created.type = reference.get_ref_from_model(triggertype)
        created.parameters = {}
        return Trigger.add_or_update(created)

    @staticmethod
    def _create_save_triggerinstance(trigger):
        created = TriggerInstanceDB()
        created.trigger = reference.get_ref_from_model(trigger)
        created.payload = {}
        created.occurrence_time = datetime.datetime.utcnow()
        return TriggerInstance.add_or_update(created)

    @staticmethod
    def _create_save_rule(trigger, action=None, enabled=True):
        created = RuleDB()
        created.name = 'rule-1'
        created.description = ''
        created.enabled = enabled
        created.trigger = reference.get_ref_from_model(trigger)
        created.criteria = {}
        created.action = ActionExecutionSpecDB()
        created.action.name = action.name
        created.action.parameters = {}
        return Rule.add_or_update(created)

    @staticmethod
    def _create_save_ruleenforcement(triggerinstance, rule,
                                     actionexecution=None):
        created = RuleEnforcementDB()
        created.rule = reference.get_ref_from_model(rule)
        created.trigger_instance = reference.get_ref_from_model(triggerinstance)
        created.action_execution = reference.get_ref_from_model(actionexecution) \
            if actionexecution else None
        return RuleEnforcement.add_or_update(created)

    @staticmethod
    def _delete(model_objects):
        global SKIP_DELETE
        if SKIP_DELETE:
            return
        for model_object in model_objects:
            model_object.delete()


from st2common.models.db.action import ActionDB, RunnerTypeDB
from st2common.persistence.action import Action, RunnerType


PARAM_SCHEMA = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "action-1",
    "description": "awesomeness",
    "type": "object",
    "properties": {
        "r1": {
            "type": "object",
            "properties": {
                "r1a": {
                    "type": "string"
                }
            }
        },
        "r2": {
            "type": "string"
        },
        "p1": {
            "type": "string"
        },
        "p2": {
            "type": "number",
            "default": 2868
        },
        "p3": {
            "type": "boolean",
            "default": False
        }
    },
    "required": ["p1", "r2"],
    "additionalProperties": False
}


@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
class ActionModelTest(DbTestCase):

    def tearDown(self):
        runnertype = RunnerType.get_by_name('python')
        self._delete([runnertype])
        super(ActionModelTest, self).tearDown()

    def test_action_crud(self):
        runnertype = self._create_save_runnertype(metadata=False)
        saved = self._create_save_action(runnertype, metadata=False)
        retrieved = Action.get_by_id(saved.id)
        self.assertEqual(saved.name, retrieved.name,
                         'Same Action was not returned.')

        # test update
        self.assertEqual(retrieved.description, 'awesomeness')
        retrieved.description = DUMMY_DESCRIPTION
        saved = Action.add_or_update(retrieved)
        retrieved = Action.get_by_id(saved.id)
        self.assertEqual(retrieved.description, DUMMY_DESCRIPTION, 'Update to action failed.')

        # cleanup
        self._delete([retrieved])
        try:
            retrieved = Action.get_by_id(saved.id)
        except ValueError:
            retrieved = None
        self.assertIsNone(retrieved, 'managed to retrieve after failure.')

    def test_parameter_schema(self):
        runnertype = self._create_save_runnertype(metadata=True)
        saved = self._create_save_action(runnertype, metadata=True)
        retrieved = Action.get_by_id(saved.id)

        # validate generated schema
        schema = util_schema.get_parameter_schema(retrieved)
        self.assertDictEqual(schema, PARAM_SCHEMA)
        validator = util_schema.get_validator()
        validator.check_schema(schema)

        # use schema to validate parameters
        jsonschema.validate({"r2": "abc", "p1": "def"}, schema)
        jsonschema.validate({"r2": "abc", "p1": "def", "r1": {"r1a": "ghi"}}, schema)
        self.assertRaises(jsonschema.ValidationError, jsonschema.validate,
                          '{"r2": "abc", "p1": "def"}', schema)
        self.assertRaises(jsonschema.ValidationError, jsonschema.validate,
                          {"r2": "abc"}, schema)
        self.assertRaises(jsonschema.ValidationError, jsonschema.validate,
                          {"r2": "abc", "p1": "def", "r1": 123}, schema)

        # cleanup
        self._delete([retrieved])
        try:
            retrieved = Action.get_by_id(saved.id)
        except ValueError:
            retrieved = None
        self.assertIsNone(retrieved, 'managed to retrieve after failure.')

    @staticmethod
    def _create_save_runnertype(metadata=False):
        created = RunnerTypeDB()
        created.name = 'python'
        created.description = ''
        created.enabled = True
        if not metadata:
            created.runner_parameters = {'r1': None, 'r2': None}
        else:
            created.runner_parameters = {
                'r1': {'type': 'object', 'properties': {'r1a': {'type': 'string'}}},
                'r2': {'type': 'string'}
            }
            created.required_parameters = ['r2']
        created.runner_module = 'nomodule'
        return RunnerType.add_or_update(created)

    @staticmethod
    def _create_save_action(runnertype, metadata=False):
        created = ActionDB()
        created.name = 'action-1'
        created.description = 'awesomeness'
        created.enabled = True
        created.entry_point = '/tmp/action.py'
        created.content_pack = 'wolfpack'
        created.runner_type = {'name': runnertype.name}
        if not metadata:
            created.parameters = {'p1': None, 'p2': None, 'p3': None}
        else:
            created.parameters = {
                'p1': {'type': 'string'},
                'p2': {'type': 'number', 'default': 2868},
                'p3': {'type': 'boolean', 'default': False}
            }
            created.required_parameters = ['p1']
        return Action.add_or_update(created)

    @staticmethod
    def _delete(model_objects):
        global SKIP_DELETE
        if SKIP_DELETE:
            return
        for model_object in model_objects:
            model_object.delete()


from st2common.models.db.datastore import KeyValuePairDB
from st2common.persistence.datastore import KeyValuePair


class KeyValuePairModelTest(DbTestCase):

    def test_kvp_crud(self):
        saved = KeyValuePairModelTest._create_save_kvp()
        retrieved = KeyValuePair.get_by_name(saved.name)
        self.assertEqual(saved.id, retrieved.id,
                         'Same KeyValuePair was not returned.')

        # test update
        self.assertEqual(retrieved.value, '0123456789ABCDEF')
        retrieved.value = 'ABCDEF0123456789'
        saved = KeyValuePair.add_or_update(retrieved)
        retrieved = KeyValuePair.get_by_name(saved.name)
        self.assertEqual(retrieved.value, 'ABCDEF0123456789',
                         'Update of key value failed')

        # cleanup
        KeyValuePairModelTest._delete([retrieved])
        try:
            retrieved = KeyValuePair.get_by_name(saved.name)
        except ValueError:
            retrieved = None
        self.assertIsNone(retrieved, 'managed to retrieve after failure.')

    @staticmethod
    def _create_save_kvp():
        created = KeyValuePairDB()
        created.name = 'token'
        created.value = '0123456789ABCDEF'
        return KeyValuePair.add_or_update(created)

    @staticmethod
    def _delete(model_objects):
        global SKIP_DELETE
        if SKIP_DELETE:
            return
        for model_object in model_objects:
            model_object.delete()
