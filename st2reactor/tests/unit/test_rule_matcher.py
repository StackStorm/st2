# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import

import six
import mock

from st2common.models.api.rule import RuleAPI
from st2common.models.db.trigger import TriggerDB, TriggerTypeDB
from st2common.persistence.rule import Rule
from st2common.persistence.trigger import TriggerType, Trigger
from st2common.services.triggers import get_trigger_db_by_ref
from st2common.util import date as date_utils
import st2reactor.container.utils as container_utils
from st2reactor.rules.matcher import RulesMatcher
from st2common.persistence.rule_enforcement import RuleEnforcement
from st2common.constants.rule_enforcement import RULE_ENFORCEMENT_STATUS_FAILED

from st2tests.base import DbTestCase
from st2tests.base import CleanDbTestCase
from st2tests.fixtures.backstop.fixture import PACK_NAME as PACK
from st2tests.fixturesloader import FixturesLoader

__all__ = ["RuleMatcherTestCase", "BackstopRuleMatcherTestCase"]

# Mock rules
RULE_1 = {
    "enabled": True,
    "name": "st2.test.rule1",
    "pack": "yoyohoneysingh",
    "trigger": {"type": "dummy_pack_1.st2.test.trigger1"},
    "criteria": {
        "k1": {  # Missing prefix 'trigger'. This rule won't match.
            "pattern": "t1_p_v",
            "type": "equals",
        }
    },
    "action": {
        "ref": "sixpack.st2.test.action",
        "parameters": {"ip2": "{{rule.k1}}", "ip1": "{{trigger.t1_p}}"},
    },
    "id": "23",
    "description": "",
}

RULE_2 = {  # Rule should match.
    "enabled": True,
    "name": "st2.test.rule2",
    "pack": "yoyohoneysingh",
    "trigger": {"type": "dummy_pack_1.st2.test.trigger1"},
    "criteria": {"trigger.k1": {"pattern": "t1_p_v", "type": "equals"}},
    "action": {
        "ref": "sixpack.st2.test.action",
        "parameters": {"ip2": "{{rule.k1}}", "ip1": "{{trigger.t1_p}}"},
    },
    "id": "23",
    "description": "",
}

RULE_3 = {
    "enabled": False,  # Disabled rule shouldn't match.
    "name": "st2.test.rule3",
    "pack": "yoyohoneysingh",
    "trigger": {"type": "dummy_pack_1.st2.test.trigger1"},
    "criteria": {"trigger.k1": {"pattern": "t1_p_v", "type": "equals"}},
    "action": {
        "ref": "sixpack.st2.test.action",
        "parameters": {"ip2": "{{rule.k1}}", "ip1": "{{trigger.t1_p}}"},
    },
    "id": "23",
    "description": "",
}

RULE_4 = {  # Rule should match.
    "enabled": True,
    "name": "st2.test.rule4",
    "pack": "yoyohoneysingh",
    "trigger": {"type": "dummy_pack_1.st2.test.trigger4"},
    "criteria": {"trigger.k1": {"pattern": "t2_p_v", "type": "equals"}},
    "action": {
        "ref": "sixpack.st2.test.action",
        "parameters": {"ip2": "{{rule.k1}}", "ip1": "{{trigger.t1_p}}"},
    },
    "id": "23",
    "description": "",
}


class RuleMatcherTestCase(CleanDbTestCase):
    rules = []

    def test_get_matching_rules(self):
        self._setup_sample_trigger("st2.test.trigger1")
        rule_db_1 = self._setup_sample_rule(RULE_1)
        rule_db_2 = self._setup_sample_rule(RULE_2)
        rule_db_3 = self._setup_sample_rule(RULE_3)
        rules = [rule_db_1, rule_db_2, rule_db_3]
        trigger_instance = container_utils.create_trigger_instance(
            "dummy_pack_1.st2.test.trigger1",
            {"k1": "t1_p_v", "k2": "v2"},
            date_utils.get_datetime_utc_now(),
        )

        trigger = get_trigger_db_by_ref(trigger_instance.trigger)
        rules_matcher = RulesMatcher(trigger_instance, trigger, rules)
        matching_rules = rules_matcher.get_matching_rules()
        self.assertIsNotNone(matching_rules)
        self.assertEqual(len(matching_rules), 1)

    def test_trigger_instance_payload_with_special_values(self):
        # Test a rule where TriggerInstance payload contains a dot (".") and $
        self._setup_sample_trigger("st2.test.trigger1")
        self._setup_sample_trigger("st2.test.trigger2")
        rule_db_1 = self._setup_sample_rule(RULE_1)
        rule_db_2 = self._setup_sample_rule(RULE_2)
        rule_db_3 = self._setup_sample_rule(RULE_3)
        rules = [rule_db_1, rule_db_2, rule_db_3]
        trigger_instance = container_utils.create_trigger_instance(
            "dummy_pack_1.st2.test.trigger2",
            {
                "k1": "t1_p_v",
                "k2.k2": "v2",
                "k3.more.nested.deep": "some.value",
                "k4.even.more.nested$": "foo",
                "yep$aaa": "b",
            },
            date_utils.get_datetime_utc_now(),
        )

        trigger = get_trigger_db_by_ref(trigger_instance.trigger)
        rules_matcher = RulesMatcher(trigger_instance, trigger, rules)
        matching_rules = rules_matcher.get_matching_rules()
        self.assertIsNotNone(matching_rules)
        self.assertEqual(len(matching_rules), 1)

    @mock.patch(
        "st2reactor.rules.matcher.RuleFilter._render_criteria_pattern",
        mock.Mock(side_effect=Exception("exception in _render_criteria_pattern")),
    )
    def test_rule_enforcement_is_created_on_exception_1(self):
        # 1. Exception in _render_criteria_pattern
        rule_enforcement_dbs = list(RuleEnforcement.get_all())
        self.assertEqual(rule_enforcement_dbs, [])

        self._setup_sample_trigger("st2.test.trigger4")
        rule_4_db = self._setup_sample_rule(RULE_4)
        rules = [rule_4_db]
        trigger_instance = container_utils.create_trigger_instance(
            "dummy_pack_1.st2.test.trigger4",
            {"k1": "t2_p_v", "k2": "v2"},
            date_utils.get_datetime_utc_now(),
        )
        trigger = get_trigger_db_by_ref(trigger_instance.trigger)

        rules_matcher = RulesMatcher(trigger_instance, trigger, rules)
        matching_rules = rules_matcher.get_matching_rules()
        self.assertEqual(matching_rules, [])
        self.assertEqual(len(matching_rules), 0)

        rule_enforcement_dbs = list(RuleEnforcement.get_all())
        self.assertEqual(len(rule_enforcement_dbs), 1)

        expected_failure = (
            'Failed to match rule "yoyohoneysingh.st2.test.rule4" against trigger '
            'instance "%s": Failed to render pattern value "t2_p_v" for key '
            '"trigger.k1": exception in _render_criteria_pattern'
            % (str(trigger_instance.id))
        )
        self.assertEqual(rule_enforcement_dbs[0].failure_reason, expected_failure)
        self.assertEqual(
            rule_enforcement_dbs[0].trigger_instance_id, str(trigger_instance.id)
        )
        self.assertEqual(rule_enforcement_dbs[0].rule["id"], str(rule_4_db.id))
        self.assertEqual(rule_enforcement_dbs[0].status, RULE_ENFORCEMENT_STATUS_FAILED)

    @mock.patch(
        "st2reactor.rules.filter.PayloadLookup.get_value",
        mock.Mock(side_effect=Exception("exception in get_value")),
    )
    def test_rule_enforcement_is_created_on_exception_2(self):
        # 1. Exception in payload_lookup.get_value
        rule_enforcement_dbs = list(RuleEnforcement.get_all())
        self.assertEqual(rule_enforcement_dbs, [])

        self._setup_sample_trigger("st2.test.trigger4")
        rule_4_db = self._setup_sample_rule(RULE_4)
        rules = [rule_4_db]
        trigger_instance = container_utils.create_trigger_instance(
            "dummy_pack_1.st2.test.trigger4",
            {"k1": "t2_p_v", "k2": "v2"},
            date_utils.get_datetime_utc_now(),
        )
        trigger = get_trigger_db_by_ref(trigger_instance.trigger)

        rules_matcher = RulesMatcher(trigger_instance, trigger, rules)
        matching_rules = rules_matcher.get_matching_rules()
        self.assertEqual(matching_rules, [])
        self.assertEqual(len(matching_rules), 0)

        rule_enforcement_dbs = list(RuleEnforcement.get_all())
        self.assertEqual(len(rule_enforcement_dbs), 1)

        expected_failure = (
            'Failed to match rule "yoyohoneysingh.st2.test.rule4" against trigger '
            'instance "%s": Failed transforming criteria key trigger.k1: '
            "exception in get_value" % (str(trigger_instance.id))
        )
        self.assertEqual(rule_enforcement_dbs[0].failure_reason, expected_failure)
        self.assertEqual(
            rule_enforcement_dbs[0].trigger_instance_id, str(trigger_instance.id)
        )
        self.assertEqual(rule_enforcement_dbs[0].rule["id"], str(rule_4_db.id))
        self.assertEqual(rule_enforcement_dbs[0].status, RULE_ENFORCEMENT_STATUS_FAILED)

    @mock.patch(
        "st2common.operators.get_operator",
        mock.Mock(return_value=mock.Mock(side_effect=Exception("exception in equals"))),
    )
    def test_rule_enforcement_is_created_on_exception_3(self):
        # 1. Exception in payload_lookup.get_value
        rule_enforcement_dbs = list(RuleEnforcement.get_all())
        self.assertEqual(rule_enforcement_dbs, [])

        self._setup_sample_trigger("st2.test.trigger4")
        rule_4_db = self._setup_sample_rule(RULE_4)
        rules = [rule_4_db]
        trigger_instance = container_utils.create_trigger_instance(
            "dummy_pack_1.st2.test.trigger4",
            {"k1": "t2_p_v", "k2": "v2"},
            date_utils.get_datetime_utc_now(),
        )
        trigger = get_trigger_db_by_ref(trigger_instance.trigger)

        rules_matcher = RulesMatcher(trigger_instance, trigger, rules)
        matching_rules = rules_matcher.get_matching_rules()
        self.assertEqual(matching_rules, [])
        self.assertEqual(len(matching_rules), 0)

        rule_enforcement_dbs = list(RuleEnforcement.get_all())
        self.assertEqual(len(rule_enforcement_dbs), 1)

        expected_failure = (
            'Failed to match rule "yoyohoneysingh.st2.test.rule4" against trigger '
            'instance "%s": There might be a problem with the criteria in rule '
            "yoyohoneysingh.st2.test.rule4: exception in equals"
            % (str(trigger_instance.id))
        )
        self.assertEqual(rule_enforcement_dbs[0].failure_reason, expected_failure)
        self.assertEqual(
            rule_enforcement_dbs[0].trigger_instance_id, str(trigger_instance.id)
        )
        self.assertEqual(rule_enforcement_dbs[0].rule["id"], str(rule_4_db.id))
        self.assertEqual(rule_enforcement_dbs[0].status, RULE_ENFORCEMENT_STATUS_FAILED)

    def _setup_sample_trigger(self, name):
        trigtype = TriggerTypeDB(
            name=name, pack="dummy_pack_1", payload_schema={}, parameters_schema={}
        )
        TriggerType.add_or_update(trigtype)

        created = TriggerDB(
            name=name,
            pack="dummy_pack_1",
            type=trigtype.get_reference().ref,
            parameters={},
        )
        Trigger.add_or_update(created)

    def _setup_sample_rule(self, rule):
        rule_api = RuleAPI(**rule)
        rule_db = RuleAPI.to_model(rule_api)
        rule_db = Rule.add_or_update(rule_db)
        return rule_db


FIXTURES_TRIGGERS = {
    "triggertypes": ["triggertype1.yaml"],
    "triggers": ["trigger1.yaml"],
}
FIXTURES_RULES = {"rules": ["backstop.yaml", "success.yaml", "fail.yaml"]}


class BackstopRuleMatcherTestCase(DbTestCase):
    models = None

    @classmethod
    def setUpClass(cls):
        super(BackstopRuleMatcherTestCase, cls).setUpClass()
        fixturesloader = FixturesLoader()
        # Create TriggerTypes before creation of Rule to avoid failure. Rule requires the
        # Trigger and therefore TriggerType to be created prior to rule creation.
        cls.models = fixturesloader.save_fixtures_to_db(
            fixtures_pack=PACK, fixtures_dict=FIXTURES_TRIGGERS
        )
        cls.models.update(
            fixturesloader.save_fixtures_to_db(
                fixtures_pack=PACK, fixtures_dict=FIXTURES_RULES
            )
        )

    def test_backstop_ignore(self):
        trigger_instance = container_utils.create_trigger_instance(
            self.models["triggers"]["trigger1.yaml"].ref,
            {"k1": "v1"},
            date_utils.get_datetime_utc_now(),
        )
        trigger = self.models["triggers"]["trigger1.yaml"]
        rules = [rule for rule in six.itervalues(self.models["rules"])]
        rules_matcher = RulesMatcher(trigger_instance, trigger, rules)
        matching_rules = rules_matcher.get_matching_rules()
        self.assertEqual(len(matching_rules), 1)
        self.assertEqual(matching_rules[0].id, self.models["rules"]["success.yaml"].id)

    def test_backstop_apply(self):
        trigger_instance = container_utils.create_trigger_instance(
            self.models["triggers"]["trigger1.yaml"].ref,
            {"k1": "v1"},
            date_utils.get_datetime_utc_now(),
        )
        trigger = self.models["triggers"]["trigger1.yaml"]
        success_rule = self.models["rules"]["success.yaml"]
        rules = [
            rule
            for rule in six.itervalues(self.models["rules"])
            if rule != success_rule
        ]
        rules_matcher = RulesMatcher(trigger_instance, trigger, rules)
        matching_rules = rules_matcher.get_matching_rules()
        self.assertEqual(len(matching_rules), 1)
        self.assertEqual(matching_rules[0].id, self.models["rules"]["backstop.yaml"].id)
