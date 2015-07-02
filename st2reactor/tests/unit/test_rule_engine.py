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

import mock
from mongoengine import NotUniqueError

from st2common.models.api.rule import RuleAPI
from st2common.models.db.trigger import (TriggerDB, TriggerTypeDB)
from st2common.persistence.rule import Rule
from st2common.persistence.trigger import (TriggerType, Trigger)
from st2common.util import date as date_utils
import st2reactor.container.utils as container_utils
from st2reactor.rules.enforcer import RuleEnforcer
from st2reactor.rules.engine import RulesEngine
from st2tests.base import DbTestCase


class RuleEngineTest(DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(RuleEngineTest, cls).setUpClass()
        RuleEngineTest._setup_test_models()

    @mock.patch.object(RuleEnforcer, 'enforce', mock.MagicMock(return_value=True))
    def test_handle_trigger_instances(self):
        trigger_instance_1 = container_utils.create_trigger_instance(
            'dummy_pack_1.st2.test.trigger1',
            {'k1': 't1_p_v', 'k2': 'v2'},
            date_utils.get_datetime_utc_now()
        )

        trigger_instance_2 = container_utils.create_trigger_instance(
            'dummy_pack_1.st2.test.trigger1',
            {'k1': 't1_p_v', 'k2': 'v2', 'k3': 'v3'},
            date_utils.get_datetime_utc_now()
        )

        trigger_instance_3 = container_utils.create_trigger_instance(
            'dummy_pack_1.st2.test.trigger2',
            {'k1': 't1_p_v', 'k2': 'v2', 'k3': 'v3'},
            date_utils.get_datetime_utc_now()
        )
        instances = [trigger_instance_1, trigger_instance_2, trigger_instance_3]
        rules_engine = RulesEngine()
        for instance in instances:
            rules_engine.handle_trigger_instance(instance)

    def test_create_trigger_instance_for_trigger_with_params(self):
        trigger = {'type': 'dummy_pack_1.st2.test.trigger4', 'parameters': {'url': 'sample'}}
        payload = {'k1': 't1_p_v', 'k2': 'v2', 'k3': 'v3'}
        occurrence_time = date_utils.get_datetime_utc_now()
        trigger_instance = container_utils.create_trigger_instance(trigger=trigger,
                                                                   payload=payload,
                                                                   occurrence_time=occurrence_time)
        self.assertTrue(trigger_instance)
        self.assertEqual(trigger_instance.trigger, trigger['type'])
        self.assertEqual(trigger_instance.payload, payload)

    def test_get_matching_rules_filters_disabled_rules(self):
        trigger_instance = container_utils.create_trigger_instance(
            'dummy_pack_1.st2.test.trigger1',
            {'k1': 't1_p_v', 'k2': 'v2'}, date_utils.get_datetime_utc_now()
        )
        rules_engine = RulesEngine()
        matching_rules = rules_engine.get_matching_rules_for_trigger(trigger_instance)
        expected_rules = ['st2.test.rule2']
        for rule in matching_rules:
            self.assertTrue(rule.name in expected_rules)

    def test_handle_trigger_instance_no_rules(self):
        trigger_instance = container_utils.create_trigger_instance(
            'dummy_pack_1.st2.test.trigger3',
            {'k1': 't1_p_v', 'k2': 'v2'},
            date_utils.get_datetime_utc_now()
        )
        rules_engine = RulesEngine()
        rules_engine.handle_trigger_instance(trigger_instance)  # should not throw.

    @classmethod
    def _setup_test_models(cls):
        RuleEngineTest._setup_sample_triggers()
        RuleEngineTest._setup_sample_rules()

    @classmethod
    def _setup_sample_triggers(self, names=['st2.test.trigger1', 'st2.test.trigger2',
                                            'st2.test.trigger3', 'st2.test.trigger4']):
        trigger_dbs = []
        for name in names:
            trigtype = None
            try:
                trigtype = TriggerTypeDB()
                trigtype.pack = 'dummy_pack_1'
                trigtype.name = name
                trigtype.description = ''
                trigtype.payload_schema = {}
                trigtype.parameters_schema = {}
                try:
                    trigtype = TriggerType.get_by_name(name)
                except:
                    trigtype = TriggerType.add_or_update(trigtype)
            except NotUniqueError:
                pass

            created = TriggerDB()
            created.name = name
            created.pack = 'dummy_pack_1'
            created.description = ''
            created.type = trigtype.get_reference().ref

            if name in ['st2.test.trigger4']:
                created.parameters = {'url': 'sample'}
            else:
                created.parameters = {}

            created = Trigger.add_or_update(created)
            trigger_dbs.append(created)

        return trigger_dbs

    @classmethod
    def _setup_sample_rules(self):
        rules = []

        # Rules for st2.test.trigger1
        RULE_1 = {
            'enabled': True,
            'name': 'st2.test.rule1',
            'pack': 'sixpack',
            'trigger': {
                'type': 'dummy_pack_1.st2.test.trigger1'
            },
            'criteria': {
                'k1': {                     # Missing prefix 'trigger'. This rule won't match.
                    'pattern': 't1_p_v',
                    'type': 'equals'
                }
            },
            'action': {
                'ref': 'sixpack.st2.test.action',
                'parameters': {
                    'ip2': '{{rule.k1}}',
                    'ip1': '{{trigger.t1_p}}'
                }
            },
            'id': '23',
            'description': ''
        }
        rule_api = RuleAPI(**RULE_1)
        rule_db = RuleAPI.to_model(rule_api)
        rule_db = Rule.add_or_update(rule_db)
        rules.append(rule_db)

        RULE_2 = {                      # Rule should match.
            'enabled': True,
            'name': 'st2.test.rule2',
            'pack': 'sixpack',
            'trigger': {
                'type': 'dummy_pack_1.st2.test.trigger1'
            },
            'criteria': {
                'trigger.k1': {
                    'pattern': 't1_p_v',
                    'type': 'equals'
                }
            },
            'action': {
                'ref': 'sixpack.st2.test.action',
                'parameters': {
                    'ip2': '{{rule.k1}}',
                    'ip1': '{{trigger.t1_p}}'
                }
            },
            'id': '23',
            'description': ''
        }
        rule_api = RuleAPI(**RULE_2)
        rule_db = RuleAPI.to_model(rule_api)
        rule_db = Rule.add_or_update(rule_db)
        rules.append(rule_db)

        RULE_3 = {
            'enabled': False,         # Disabled rule shouldn't match.
            'name': 'st2.test.rule3',
            'pack': 'sixpack',
            'trigger': {
                'type': 'dummy_pack_1.st2.test.trigger1'
            },
            'criteria': {
                'trigger.k1': {
                    'pattern': 't1_p_v',
                    'type': 'equals'
                }
            },
            'action': {
                'ref': 'sixpack.st2.test.action',
                'parameters': {
                    'ip2': '{{rule.k1}}',
                    'ip1': '{{trigger.t1_p}}'
                }
            },
            'id': '23',
            'description': ''
        }
        rule_api = RuleAPI(**RULE_3)
        rule_db = RuleAPI.to_model(rule_api)
        rule_db = Rule.add_or_update(rule_db)
        rules.append(rule_db)

        # Rules for st2.test.trigger2
        RULE_4 = {
            'enabled': True,
            'name': 'st2.test.rule4',
            'pack': 'sixpack',
            'trigger': {
                'type': 'dummy_pack_1.st2.test.trigger2'
            },
            'criteria': {
                'trigger.k1': {
                    'pattern': 't1_p_v',
                    'type': 'equals'
                }
            },
            'action': {
                'ref': 'sixpack.st2.test.action',
                'parameters': {
                    'ip2': '{{rule.k1}}',
                    'ip1': '{{trigger.t1_p}}'
                }
            },
            'id': '23',
            'description': ''
        }
        rule_api = RuleAPI(**RULE_4)
        rule_db = RuleAPI.to_model(rule_api)
        rule_db = Rule.add_or_update(rule_db)
        rules.append(rule_db)

        return rules
