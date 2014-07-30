import datetime
import mongoengine.connection
from oslo.config import cfg
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


from st2common.models.db.reactor import TriggerDB, TriggerInstanceDB, \
    TriggerSourceDB, RuleEnforcementDB, RuleDB, ActionExecutionSpecDB
from st2common.persistence.reactor import Trigger, TriggerInstance, \
    TriggerSource, RuleEnforcement, Rule


class ReactorModelTest(DbTestCase):

    def test_triggersource_crud(self):
        saved = ReactorModelTest._create_save_triggersource()
        retrieved = TriggerSource.get_by_id(saved.id)
        self.assertEqual(saved.name, retrieved.name,
                         'Same TriggerSource was not returned.')
        ReactorModelTest._delete([retrieved])
        try:
            retrieved = TriggerSource.get_by_id(saved.id)
        except ValueError:
            retrieved = None
        self.assertIsNone(retrieved, 'managed to retrieve after failure.')

    def test_trigger_crud(self):
        triggersource = ReactorModelTest._create_save_triggersource()
        saved = ReactorModelTest._create_save_trigger(triggersource)
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
        ReactorModelTest._delete([retrieved, triggersource])
        try:
            retrieved = Trigger.get_by_id(saved.id)
        except ValueError:
            retrieved = None
        self.assertIsNone(retrieved, 'managed to retrieve after failure.')

    def test_triggerinstance_crud(self):
        triggersource = ReactorModelTest._create_save_triggersource()
        trigger = ReactorModelTest._create_save_trigger(triggersource)
        saved = ReactorModelTest._create_save_triggerinstance(trigger)
        retrieved = TriggerInstance.get_by_id(saved.id)
        self.assertIsNotNone(retrieved, 'No triggerinstance created.')
        ReactorModelTest._delete([retrieved, trigger, triggersource])
        try:
            retrieved = TriggerInstance.get_by_id(saved.id)
        except ValueError:
            retrieved = None
        self.assertIsNone(retrieved, 'managed to retrieve after failure.')

    def test_rule_crud(self):
        triggersource = ReactorModelTest._create_save_triggersource()
        actiontype = ActionModelTest._create_save_actiontype()
        action = ActionModelTest._create_save_action(actiontype)
        trigger = ReactorModelTest._create_save_trigger(triggersource)
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
        ReactorModelTest._delete([retrieved, trigger, action, actiontype, triggersource])
        try:
            retrieved = Rule.get_by_id(saved.id)
        except ValueError:
            retrieved = None
        self.assertIsNone(retrieved, 'managed to retrieve after failure.')

    def test_ruleenforcement_crud(self):
        triggersource = ReactorModelTest._create_save_triggersource()
        trigger = ReactorModelTest._create_save_trigger(triggersource)
        actiontype = ActionModelTest._create_save_actiontype()
        action = ActionModelTest._create_save_action(actiontype)
        triggerinstance = ReactorModelTest._create_save_triggerinstance(trigger)
        rule = ReactorModelTest._create_save_rule(trigger, action)
        saved = ReactorModelTest._create_save_ruleenforcement(triggerinstance,
                                                              rule)
        retrieved = RuleEnforcement.get_by_id(saved.id)
        self.assertIsNotNone(retrieved, 'No ruleenforcement created.')
        ReactorModelTest._delete([retrieved, rule, triggerinstance, trigger,
                                  action, actiontype, triggersource])
        try:
            retrieved = RuleEnforcement.get_by_id(saved.id)
        except ValueError:
            retrieved = None
        self.assertIsNone(retrieved, 'managed to retrieve after failure.')

    def test_rule_lookup(self):
        triggersource = ReactorModelTest._create_save_triggersource()
        actiontype = ActionModelTest._create_save_actiontype()
        action = ActionModelTest._create_save_action(actiontype)
        trigger = ReactorModelTest._create_save_trigger(triggersource)
        saved = ReactorModelTest._create_save_rule(trigger, action)
        retrievedrules = Rule.query(trigger=reference.get_ref_from_model(trigger))
        self.assertEqual(1, len(retrievedrules), 'No rules found.')
        for retrievedrule in retrievedrules:
            self.assertEqual(saved.id, retrievedrule.id,
                             'Incorrect rule returned.')
        ReactorModelTest._delete([saved, trigger, action, actiontype, triggersource])

    def test_rule_lookup_enabled(self):
        triggersource = ReactorModelTest._create_save_triggersource()
        actiontype = ActionModelTest._create_save_actiontype()
        action = ActionModelTest._create_save_action(actiontype)
        trigger = ReactorModelTest._create_save_trigger(triggersource)
        saved = ReactorModelTest._create_save_rule(trigger, action)
        retrievedrules = Rule.query(trigger=reference.get_ref_from_model(trigger),
                                    enabled=True)
        self.assertEqual(1, len(retrievedrules), 'Error looking up enabled rules.')
        for retrievedrule in retrievedrules:
            self.assertEqual(saved.id, retrievedrule.id,
                             'Incorrect rule returned.')
        ReactorModelTest._delete([saved, trigger, action, actiontype, triggersource])

    def test_rule_lookup_disabled(self):
        triggersource = ReactorModelTest._create_save_triggersource()
        actiontype = ActionModelTest._create_save_actiontype()
        action = ActionModelTest._create_save_action(actiontype)
        trigger = ReactorModelTest._create_save_trigger(triggersource)
        saved = ReactorModelTest._create_save_rule(trigger, action, False)
        retrievedrules = Rule.query(trigger=reference.get_ref_from_model(trigger),
                                    enabled=False)
        self.assertEqual(1, len(retrievedrules), 'Error looking up enabled rules.')
        for retrievedrule in retrievedrules:
            self.assertEqual(saved.id, retrievedrule.id,
                             'Incorrect rule returned.')
        ReactorModelTest._delete([saved, trigger, action, actiontype, triggersource])

    def test_trigger_lookup(self):
        triggersource = ReactorModelTest._create_save_triggersource()
        saved = ReactorModelTest._create_save_trigger(triggersource)
        retrievedtriggers = Trigger.query(name=saved.name)
        self.assertEqual(1, len(retrievedtriggers), 'No triggers found.')
        for retrievedtrigger in retrievedtriggers:
            self.assertEqual(saved.id, retrievedtrigger.id,
                             'Incorrect trigger returned.')
        ReactorModelTest._delete([saved, triggersource])

    @staticmethod
    def _create_save_triggersource():
        created = TriggerSourceDB()
        created.name = 'triggersource-1'
        created.description = ''
        return TriggerSource.add_or_update(created)

    @staticmethod
    def _create_save_trigger(triggersource):
        created = TriggerDB()
        created.name = 'trigger-1'
        created.description = ''
        created.payload_info = []
        created.trigger_source = triggersource
        return TriggerSource.add_or_update(created)

    @staticmethod
    def _create_save_triggerinstance(trigger):
        created = TriggerInstanceDB()
        created.trigger = reference.get_ref_from_model(trigger)
        created.payload = {}
        created.occurrence_time = datetime.datetime.now()
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
        created.action.action = reference.get_ref_from_model(action)
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


from st2common.models.db.action import ActionDB, ActionTypeDB
from st2common.persistence.action import Action, ActionType


class ActionModelTest(DbTestCase):

    def test_action_crud(self):
        actiontype = ActionModelTest._create_save_actiontype()
        saved = ActionModelTest._create_save_action(actiontype)
        retrieved = Action.get_by_id(saved.id)
        self.assertEqual(saved.name, retrieved.name,
                         'Same TriggerSource was not returned.')
        # test update
        self.assertEqual(retrieved.description, '')
        retrieved.description = DUMMY_DESCRIPTION
        saved = Action.add_or_update(retrieved)
        retrieved = Action.get_by_id(saved.id)
        self.assertEqual(retrieved.description, DUMMY_DESCRIPTION, 'Update to action failed.')
        # cleanup
        ActionModelTest._delete([retrieved])
        try:
            retrieved = Action.get_by_id(saved.id)
        except ValueError:
            retrieved = None
        self.assertIsNone(retrieved, 'managed to retrieve after failure.')

    @staticmethod
    def _create_save_actiontype():
        created = ActionTypeDB()
        created.name = 'python'
        created.description = ''
        created.enabled = True
        created.runner_parameters = {'r1': None, 'r2': None}
        created.runner_module = 'nomodule'
        return ActionType.add_or_update(created)

    @staticmethod
    def _create_save_action(actiontype):
        created = ActionDB()
        created.name = 'action-1'
        created.description = ''
        created.enabled = True
        created.artifact_path = ''
        created.entry_point = '/tmp/action.py'
        created.runner_type = actiontype
        created.parameters = {'p1': None, 'p2': None, 'p3': None}
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
