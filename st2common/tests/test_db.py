import tests
import unittest2
import mongoengine.connection
from oslo.config import cfg
from st2common.models.db import setup, teardown


SKIP_DELETE = False


class DbConnectionTest(unittest2.TestCase):
    def setUp(self):
        tests.parse_args()
        setup()

    def tearDown(self):
        teardown()

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
    TriggerSourceDB, RuleEnforcementDB, RuleDB
from st2common.persistence.reactor import Trigger, TriggerInstance, \
    TriggerSource, RuleEnforcement, Rule


class ReactorModelTest(unittest2.TestCase):
    def setUp(self):
        tests.parse_args()
        setup()

    def tearDown(self):
        teardown()

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
        trigger = ReactorModelTest._create_save_trigger(triggersource)
        saved = ReactorModelTest._create_save_rule(trigger)
        retrieved = Rule.get_by_id(saved.id)
        self.assertEqual(saved.name, retrieved.name,
                         'Same rule was not returned.')
        ReactorModelTest._delete([retrieved, trigger, triggersource])
        try:
            retrieved = Rule.get_by_id(saved.id)
        except ValueError:
            retrieved = None
        self.assertIsNone(retrieved, 'managed to retrieve after failure.')

    def test_ruleenforcement_crud(self):
        triggersource = ReactorModelTest._create_save_triggersource()
        trigger = ReactorModelTest._create_save_trigger(triggersource)
        triggerinstance = ReactorModelTest._create_save_triggerinstance(trigger)
        rule = ReactorModelTest._create_save_rule(trigger)
        saved = ReactorModelTest._create_save_ruleenforcement(triggerinstance,
                                                              rule)
        retrieved = RuleEnforcement.get_by_id(saved.id)
        self.assertEqual(saved.name, retrieved.name,
                         'Same rule was not returned.')
        ReactorModelTest._delete([retrieved,rule, triggerinstance, trigger,
                                  triggersource])
        try:
            retrieved = Rule.get_by_id(saved.id)
        except ValueError:
            retrieved = None
        self.assertIsNone(retrieved, 'managed to retrieve after failure.')

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
        return TriggerInstance.add_or_update(created)

    @staticmethod
    def _create_save_rule(trigger, staction=None):
        created = RuleDB()
        created.name = 'rule-1'
        created.description = ''
        created.trigger = trigger
        created.staction = staction
        created.data_mapping = {}
        return Rule.add_or_update(created)

    @staticmethod
    def _create_save_ruleenforcement(triggerinstance, rule,
                                     stactionexecution=None):
        created = RuleEnforcementDB()
        created.name = 'ruleenforcement-1'
        created.description = ''
        created.rule = rule
        created.trigger_instance = triggerinstance
        created.staction_execution = stactionexecution
        return RuleEnforcement.add_or_update(created)

    @staticmethod
    def _delete(model_objects):
        global SKIP_DELETE
        if SKIP_DELETE:
            return
        for model_object in model_objects:
            model_object.delete()
