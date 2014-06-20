import datetime
import tests
import mongoengine.connection
from oslo.config import cfg

SKIP_DELETE = False


class DbConnectionTest(tests.DbTestCase):

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


class ReactorModelTest(tests.DbTestCase):

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
        self.assertEqual(saved.name, retrieved.name,
                         'Same triggerinstance was not returned.')
        ReactorModelTest._delete([retrieved, trigger, triggersource])
        try:
            retrieved = TriggerInstance.get_by_id(saved.id)
        except ValueError:
            retrieved = None
        self.assertIsNone(retrieved, 'managed to retrieve after failure.')

    def test_rule_crud(self):
        triggersource = ReactorModelTest._create_save_triggersource()
        action = ActionModelTest._create_save_action()
        trigger = ReactorModelTest._create_save_trigger(triggersource)
        saved = ReactorModelTest._create_save_rule(trigger, action)
        retrieved = Rule.get_by_id(saved.id)
        self.assertEqual(saved.name, retrieved.name,
                         'Same rule was not returned.')
        ReactorModelTest._delete([retrieved, trigger, action, triggersource])
        try:
            retrieved = Rule.get_by_id(saved.id)
        except ValueError:
            retrieved = None
        self.assertIsNone(retrieved, 'managed to retrieve after failure.')

    def test_ruleenforcement_crud(self):
        triggersource = ReactorModelTest._create_save_triggersource()
        trigger = ReactorModelTest._create_save_trigger(triggersource)
        action = ActionModelTest._create_save_action()
        triggerinstance = ReactorModelTest._create_save_triggerinstance(trigger)
        rule = ReactorModelTest._create_save_rule(trigger, action)
        saved = ReactorModelTest._create_save_ruleenforcement(triggerinstance,
                                                              rule)
        retrieved = RuleEnforcement.get_by_id(saved.id)
        self.assertEqual(saved.name, retrieved.name,
                         'Same rule was not returned.')
        ReactorModelTest._delete([retrieved, rule, triggerinstance, trigger,
                                  triggersource])
        try:
            retrieved = RuleEnforcement.get_by_id(saved.id)
        except ValueError:
            retrieved = None
        self.assertIsNone(retrieved, 'managed to retrieve after failure.')

    def test_rule_lookup(self):
        triggersource = ReactorModelTest._create_save_triggersource()
        action = ActionModelTest._create_save_action()
        trigger = ReactorModelTest._create_save_trigger(triggersource)
        saved = ReactorModelTest._create_save_rule(trigger, action)
        retrievedrules = Rule.query(trigger_type=trigger)
        self.assertEqual(2, len(retrievedrules), 'No rules found.')
        for retrievedrule in retrievedrules:
            self.assertEqual(saved.id, retrievedrule.id,
                             'Incorrect rule returned.')
        ReactorModelTest._delete([saved, trigger, action, triggersource])

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
        created.name = 'triggerinstance-1'
        created.description = ''
        created.trigger = trigger
        created.payload = {}
        created.occurrence_time = datetime.datetime.now()
        return TriggerInstance.add_or_update(created)

    @staticmethod
    def _create_save_rule(trigger, action=None):
        created = RuleDB()
        created.name = 'rule-1'
        created.description = ''
        created.trigger_type = trigger
        created.criteria = {}
        created.action = ActionExecutionSpecDB()
        created.action.action = action
        created.action.data_mapping = {}
        return Rule.add_or_update(created)

    @staticmethod
    def _create_save_ruleenforcement(triggerinstance, rule,
                                     actionexecution=None):
        created = RuleEnforcementDB()
        created.name = 'ruleenforcement-1'
        created.description = ''
        created.rule = rule
        created.trigger_instance = triggerinstance
        created.action_execution = actionexecution
        return RuleEnforcement.add_or_update(created)

    @staticmethod
    def _delete(model_objects):
        global SKIP_DELETE
        if SKIP_DELETE:
            return
        for model_object in model_objects:
            model_object.delete()


from st2common.models.db.action import ActionDB
from st2common.persistence.action import Action


class ActionModelTest(tests.DbTestCase):

    def test_action_crud(self):
        saved = ActionModelTest._create_save_action()
        retrieved = Action.get_by_id(saved.id)
        self.assertEqual(saved.name, retrieved.name,
                         'Same TriggerSource was not returned.')
        ActionModelTest._delete([retrieved])
        try:
            retrieved = Action.get_by_id(saved.id)
        except ValueError:
            retrieved = None
        self.assertIsNone(retrieved, 'managed to retrieve after failure.')

    @staticmethod
    def _create_save_action():
        created = ActionDB()
        created.name = 'action-1'
        created.description = ''
        created.enabled = True
        created.artifact_path = '/tmp/action.py'
        created.entry_point = ''
        # created.run_type = 'python'
        # created.parameter_names = ['p1', 'p2', 'p3']
        return Action.add_or_update(created)

    @staticmethod
    def _delete(model_objects):
        global SKIP_DELETE
        if SKIP_DELETE:
            return
        for model_object in model_objects:
            model_object.delete()
