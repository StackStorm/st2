import copy

from st2common.models.api.rule import RuleAPI
from st2common.models.system.common import ResourceReference
from st2common.persistence.reactor import Trigger
import st2common.services.triggers as trigger_service

from st2tests.base import CleanDbTestCase
from st2tests.fixturesloader import FixturesLoader


class TriggerServiceTests(CleanDbTestCase):

    def test_create_trigger_db_from_rule(self):
        test_fixtures = {
            'rules': ['cron_timer_rule_1.json', 'cron_timer_rule_3.json']
        }
        loader = FixturesLoader()
        fixtures = loader.load_fixtures(fixtures_pack='generic', fixtures_dict=test_fixtures)
        rules = fixtures['rules']

        trigger_db_ret_1 = trigger_service.create_trigger_db_from_rule(
            RuleAPI(**rules['cron_timer_rule_1.json']))
        self.assertTrue(trigger_db_ret_1 is not None)
        trigger_db = Trigger.get_by_id(trigger_db_ret_1.id)
        self.assertDictEqual(trigger_db.parameters,
                             rules['cron_timer_rule_1.json']['trigger']['parameters'])

        trigger_db_ret_2 = trigger_service.create_trigger_db_from_rule(
            RuleAPI(**rules['cron_timer_rule_3.json']))
        self.assertTrue(trigger_db_ret_2 is not None)
        self.assertTrue(trigger_db_ret_2.id != trigger_db_ret_1.id)

    def test_create_trigger_db_from_rule_duplicate(self):
        test_fixtures = {
            'rules': ['cron_timer_rule_1.json', 'cron_timer_rule_2.json']
        }
        loader = FixturesLoader()
        fixtures = loader.load_fixtures(fixtures_pack='generic', fixtures_dict=test_fixtures)
        rules = fixtures['rules']

        trigger_db_ret_1 = trigger_service.create_trigger_db_from_rule(
            RuleAPI(**rules['cron_timer_rule_1.json']))
        self.assertTrue(trigger_db_ret_1 is not None)
        trigger_db_ret_2 = trigger_service.create_trigger_db_from_rule(
            RuleAPI(**rules['cron_timer_rule_2.json']))
        self.assertTrue(trigger_db_ret_2 is not None)
        self.assertEqual(trigger_db_ret_1, trigger_db_ret_2, 'Should reuse same trigger.')
        trigger_db = Trigger.get_by_id(trigger_db_ret_1.id)
        self.assertDictEqual(trigger_db.parameters,
                             rules['cron_timer_rule_1.json']['trigger']['parameters'])

    def test_create_trigger_db_from_rule_use_ref_for_trigger(self):
        test_fixtures = {
            'rules': ['cron_timer_rule_1.json']
        }
        loader = FixturesLoader()
        fixtures = loader.load_fixtures(fixtures_pack='generic', fixtures_dict=test_fixtures)
        rules = fixtures['rules']
        rule_api = RuleAPI(**rules['cron_timer_rule_1.json'])
        trigger_db_ret_1 = trigger_service.create_trigger_db_from_rule(rule_api)
        self.assertTrue(trigger_db_ret_1 is not None)
        rule_api2 = copy.copy(rule_api)
        ref = ResourceReference.to_string_reference(name=trigger_db_ret_1.name,
                                                    pack=trigger_db_ret_1.pack)
        rule_api2.trigger = {'ref': ref, 'type': trigger_db_ret_1.type}
        trigger_db_ret_2 = trigger_service.create_trigger_db_from_rule(rule_api2)
        self.assertTrue(trigger_db_ret_2 is not None)
        self.assertTrue(trigger_db_ret_2.id == trigger_db_ret_1.id)

    def test_create_or_update_trigger_db(self):
        test_fixtures = {
            'triggertypes': ['triggertype1.json']
        }
        loader = FixturesLoader()
        fixtures = loader.save_fixtures_to_db(fixtures_pack='generic', fixtures_dict=test_fixtures)
        triggertypes = fixtures['triggertypes']
        trigger_type_ref = ResourceReference.to_string_reference(
            name=triggertypes['triggertype1.json']['name'],
            pack=triggertypes['triggertype1.json']['name'])

        trigger = {
            'name': 'foo',
            'pack': 'st2',
            'type': trigger_type_ref
        }
        trigger_service.create_or_update_trigger_db(trigger)
        triggers = Trigger.get_all()
        self.assertTrue(len(triggers) == 1, 'Only one trigger should be created.')
        self.assertTrue(triggers[0]['name'] == 'foo')

        # Try adding duplicate
        trigger_service.create_or_update_trigger_db(trigger)
        triggers = Trigger.get_all()
        self.assertTrue(len(triggers) == 1, 'Only one trigger should be present.')
        self.assertTrue(triggers[0]['name'] == 'foo')
