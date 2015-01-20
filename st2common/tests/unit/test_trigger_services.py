# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from st2common.exceptions.triggers import TriggerDoesNotExistException
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

    def test_create_or_update_trigger_db_simple_triggers(self):
        test_fixtures = {
            'triggertypes': ['triggertype1.json']
        }
        loader = FixturesLoader()
        fixtures = loader.save_fixtures_to_db(fixtures_pack='generic', fixtures_dict=test_fixtures)
        triggertypes = fixtures['triggertypes']
        trigger_type_ref = ResourceReference.to_string_reference(
            name=triggertypes['triggertype1.json']['name'],
            pack=triggertypes['triggertype1.json']['pack'])

        trigger = {
            'name': triggertypes['triggertype1.json']['name'],
            'pack': triggertypes['triggertype1.json']['pack'],
            'type': trigger_type_ref
        }
        trigger_service.create_or_update_trigger_db(trigger)
        triggers = Trigger.get_all()
        self.assertTrue(len(triggers) == 1, 'Only one trigger should be created.')
        self.assertTrue(triggers[0]['name'] == triggertypes['triggertype1.json']['name'])

        # Try adding duplicate
        trigger_service.create_or_update_trigger_db(trigger)
        triggers = Trigger.get_all()
        self.assertTrue(len(triggers) == 1, 'Only one trigger should be present.')
        self.assertTrue(triggers[0]['name'] == triggertypes['triggertype1.json']['name'])

    def test_exception_thrown_when_rule_creation_no_trigger_yes_triggertype(self):
        test_fixtures = {
            'triggertypes': ['triggertype1.json']
        }
        loader = FixturesLoader()
        fixtures = loader.save_fixtures_to_db(fixtures_pack='generic', fixtures_dict=test_fixtures)
        triggertypes = fixtures['triggertypes']
        trigger_type_ref = ResourceReference.to_string_reference(
            name=triggertypes['triggertype1.json']['name'],
            pack=triggertypes['triggertype1.json']['pack'])

        rule = {
            'name': 'fancyrule',
            'trigger': {
                'type': trigger_type_ref
            },
            'criteria': {

            },
            'action': {
                'ref': 'core.local',
                'parameters': {
                    'cmd': 'date'
                }
            }
        }
        rule_api = RuleAPI(**rule)
        self.assertRaises(TriggerDoesNotExistException,
                          trigger_service.create_trigger_db_from_rule, rule_api)
