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
from st2common.models.db.trigger import TriggerDB
from st2common.persistence.trigger import (Trigger, TriggerType)
import st2common.services.triggers as trigger_service

from st2tests.base import CleanDbTestCase
from st2tests.fixturesloader import FixturesLoader

MOCK_TRIGGER = TriggerDB()
MOCK_TRIGGER.id = 'trigger-test.id'
MOCK_TRIGGER.name = 'trigger-test.name'
MOCK_TRIGGER.pack = 'dummy_pack_1'
MOCK_TRIGGER.parameters = {}
MOCK_TRIGGER.type = 'dummy_pack_1.trigger-type-test.name'


class TriggerServiceTests(CleanDbTestCase):

    def test_create_trigger_db_from_rule(self):
        test_fixtures = {
            'rules': ['cron_timer_rule_1.yaml', 'cron_timer_rule_3.yaml']
        }
        loader = FixturesLoader()
        fixtures = loader.load_fixtures(fixtures_pack='generic', fixtures_dict=test_fixtures)
        rules = fixtures['rules']

        trigger_db_ret_1 = trigger_service.create_trigger_db_from_rule(
            RuleAPI(**rules['cron_timer_rule_1.yaml']))
        self.assertTrue(trigger_db_ret_1 is not None)
        trigger_db = Trigger.get_by_id(trigger_db_ret_1.id)
        self.assertDictEqual(trigger_db.parameters,
                             rules['cron_timer_rule_1.yaml']['trigger']['parameters'])

        trigger_db_ret_2 = trigger_service.create_trigger_db_from_rule(
            RuleAPI(**rules['cron_timer_rule_3.yaml']))
        self.assertTrue(trigger_db_ret_2 is not None)
        self.assertTrue(trigger_db_ret_2.id != trigger_db_ret_1.id)

    def test_create_trigger_db_from_rule_duplicate(self):
        test_fixtures = {
            'rules': ['cron_timer_rule_1.yaml', 'cron_timer_rule_2.yaml']
        }
        loader = FixturesLoader()
        fixtures = loader.load_fixtures(fixtures_pack='generic', fixtures_dict=test_fixtures)
        rules = fixtures['rules']

        trigger_db_ret_1 = trigger_service.create_trigger_db_from_rule(
            RuleAPI(**rules['cron_timer_rule_1.yaml']))
        self.assertTrue(trigger_db_ret_1 is not None)
        trigger_db_ret_2 = trigger_service.create_trigger_db_from_rule(
            RuleAPI(**rules['cron_timer_rule_2.yaml']))
        self.assertTrue(trigger_db_ret_2 is not None)
        self.assertEqual(trigger_db_ret_1, trigger_db_ret_2, 'Should reuse same trigger.')
        trigger_db = Trigger.get_by_id(trigger_db_ret_1.id)
        self.assertDictEqual(trigger_db.parameters,
                             rules['cron_timer_rule_1.yaml']['trigger']['parameters'])

    def test_create_or_update_trigger_db_simple_triggers(self):
        test_fixtures = {
            'triggertypes': ['triggertype1.yaml']
        }
        loader = FixturesLoader()
        fixtures = loader.save_fixtures_to_db(fixtures_pack='generic', fixtures_dict=test_fixtures)
        triggertypes = fixtures['triggertypes']
        trigger_type_ref = ResourceReference.to_string_reference(
            name=triggertypes['triggertype1.yaml']['name'],
            pack=triggertypes['triggertype1.yaml']['pack'])

        trigger = {
            'name': triggertypes['triggertype1.yaml']['name'],
            'pack': triggertypes['triggertype1.yaml']['pack'],
            'type': trigger_type_ref
        }
        trigger_service.create_or_update_trigger_db(trigger)
        triggers = Trigger.get_all()
        self.assertTrue(len(triggers) == 1, 'Only one trigger should be created.')
        self.assertTrue(triggers[0]['name'] == triggertypes['triggertype1.yaml']['name'])

        # Try adding duplicate
        trigger_service.create_or_update_trigger_db(trigger)
        triggers = Trigger.get_all()
        self.assertTrue(len(triggers) == 1, 'Only one trigger should be present.')
        self.assertTrue(triggers[0]['name'] == triggertypes['triggertype1.yaml']['name'])

    def test_exception_thrown_when_rule_creation_no_trigger_yes_triggertype(self):
        test_fixtures = {
            'triggertypes': ['triggertype1.yaml']
        }
        loader = FixturesLoader()
        fixtures = loader.save_fixtures_to_db(fixtures_pack='generic', fixtures_dict=test_fixtures)
        triggertypes = fixtures['triggertypes']
        trigger_type_ref = ResourceReference.to_string_reference(
            name=triggertypes['triggertype1.yaml']['name'],
            pack=triggertypes['triggertype1.yaml']['pack'])

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

    def test_get_trigger_db_given_type_and_params(self):
        # Add dummy triggers
        trigger_1 = TriggerDB()
        trigger_1.pack = 'testpack'
        trigger_1.name = 'testtrigger1'
        trigger_1.type = 'testpack.testtrigger1'
        trigger_1.parameters = {}

        trigger_2 = TriggerDB()
        trigger_2.pack = 'testpack'
        trigger_2.name = 'testtrigger2'
        trigger_2.type = 'testpack.testtrigger2'
        trigger_2.parameters = None

        trigger_3 = TriggerDB()
        trigger_3.pack = 'testpack'
        trigger_3.name = 'testtrigger3'
        trigger_3.type = 'testpack.testtrigger3'

        trigger_4 = TriggerDB()
        trigger_4.pack = 'testpack'
        trigger_4.name = 'testtrigger4'
        trigger_4.type = 'testpack.testtrigger4'
        trigger_4.parameters = {'ponies': 'unicorn'}

        Trigger.add_or_update(trigger_1)
        Trigger.add_or_update(trigger_2)
        Trigger.add_or_update(trigger_3)
        Trigger.add_or_update(trigger_4)

        # Trigger with no parameters, parameters={} in db
        trigger_db = trigger_service.get_trigger_db_given_type_and_params(type=trigger_1.type,
                                                                          parameters={})
        self.assertEqual(trigger_db, trigger_1)

        trigger_db = trigger_service.get_trigger_db_given_type_and_params(type=trigger_1.type,
                                                                          parameters=None)
        self.assertEqual(trigger_db, trigger_1)

        trigger_db = trigger_service.get_trigger_db_given_type_and_params(type=trigger_1.type,
                                                                          parameters={'fo': 'bar'})
        self.assertEqual(trigger_db, None)

        # Trigger with no parameters, no parameters attribute in the db
        trigger_db = trigger_service.get_trigger_db_given_type_and_params(type=trigger_2.type,
                                                                          parameters={})
        self.assertEqual(trigger_db, trigger_2)

        trigger_db = trigger_service.get_trigger_db_given_type_and_params(type=trigger_2.type,
                                                                          parameters=None)
        self.assertEqual(trigger_db, trigger_2)

        trigger_db = trigger_service.get_trigger_db_given_type_and_params(type=trigger_2.type,
                                                                          parameters={'fo': 'bar'})
        self.assertEqual(trigger_db, None)

        trigger_db = trigger_service.get_trigger_db_given_type_and_params(type=trigger_3.type,
                                                                          parameters={})
        self.assertEqual(trigger_db, trigger_3)

        trigger_db = trigger_service.get_trigger_db_given_type_and_params(type=trigger_3.type,
                                                                          parameters=None)
        self.assertEqual(trigger_db, trigger_3)

        # Trigger with parameters
        trigger_db = trigger_service.get_trigger_db_given_type_and_params(
            type=trigger_4.type,
            parameters=trigger_4.parameters)
        self.assertEqual(trigger_db, trigger_4)

        trigger_db = trigger_service.get_trigger_db_given_type_and_params(type=trigger_4.type,
                                                                          parameters=None)
        self.assertEqual(trigger_db, None)

    def test_add_trigger_type_no_params(self):
        # Trigger type with no params should create a trigger with same name as trigger type.
        trig_type = {
            'name': 'myawesometriggertype',
            'pack': 'dummy_pack_1',
            'description': 'Words cannot describe how awesome I am.',
            'parameters_schema': {},
            'payload_schema': {}
        }
        trigtype_dbs = trigger_service.add_trigger_models(trigger_types=[trig_type])
        trigger_type, trigger = trigtype_dbs[0]

        trigtype_db = TriggerType.get_by_id(trigger_type.id)
        self.assertEqual(trigtype_db.pack, 'dummy_pack_1')
        self.assertEqual(trigtype_db.name, trig_type.get('name'))
        self.assertTrue(trigger is not None)
        self.assertEqual(trigger.name, trigtype_db.name)

        # Add duplicate
        trigtype_dbs = trigger_service.add_trigger_models(trigger_types=[trig_type])
        triggers = Trigger.get_all()
        self.assertTrue(len(triggers) == 1)

    def test_add_trigger_type_with_params(self):
        MOCK_TRIGGER.type = 'system.test'
        # Trigger type with params should not create a trigger.
        PARAMETERS_SCHEMA = {
            "type": "object",
            "properties": {
                "url": {"type": "string"}
            },
            "required": ['url'],
            "additionalProperties": False
        }
        trig_type = {
            'name': 'myawesometriggertype2',
            'pack': 'my_pack_1',
            'description': 'Words cannot describe how awesome I am.',
            'parameters_schema': PARAMETERS_SCHEMA,
            'payload_schema': {}
        }
        trigtype_dbs = trigger_service.add_trigger_models(trigger_types=[trig_type])
        trigger_type, trigger = trigtype_dbs[0]

        trigtype_db = TriggerType.get_by_id(trigger_type.id)
        self.assertEqual(trigtype_db.pack, 'my_pack_1')
        self.assertEqual(trigtype_db.name, trig_type.get('name'))
        self.assertEqual(trigger, None)

    def test_add_trigger_type(self):
        """
        This sensor has misconfigured trigger type. We shouldn't explode.
        """
        class FailTestSensor(object):
            started = False

            def setup(self):
                pass

            def start(self):
                FailTestSensor.started = True

            def stop(self):
                pass

            def get_trigger_types(self):
                return [
                    {'description': 'Ain\'t got no name'}
                ]

        try:
            trigger_service.add_trigger_models(FailTestSensor().get_trigger_types())
            self.assertTrue(False, 'Trigger type doesn\'t have \'name\' field. Should have thrown.')
        except Exception:
            self.assertTrue(True)
