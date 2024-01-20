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

# pytest: make sure monkey_patching happens before importing mongoengine
from st2common.util.monkey_patch import monkey_patch

monkey_patch()

import mock

from st2common.constants import action as action_constants
from st2common.constants.keyvalue import FULL_SYSTEM_SCOPE
from st2common.constants.rule_enforcement import RULE_ENFORCEMENT_STATUS_SUCCEEDED
from st2common.constants.rule_enforcement import RULE_ENFORCEMENT_STATUS_FAILED
from st2common.expressions.functions import data
from st2common.models.db.trigger import TriggerInstanceDB
from st2common.models.db.execution import ActionExecutionDB
from st2common.models.db.liveaction import LiveActionDB
from st2common.models.db.keyvalue import KeyValuePairDB
from st2common.persistence.keyvalue import KeyValuePair
from st2common.persistence.rule_enforcement import RuleEnforcement
from st2common.services import action as action_service
from st2common.bootstrap import runnersregistrar as runners_registrar
from st2common.util import casts
from st2common.util import reference
from st2common.util import date as date_utils
from st2reactor.rules.enforcer import RuleEnforcer

from st2tests import DbTestCase
from st2tests.fixtures.generic.fixture import PACK_NAME as PACK
from st2tests.fixturesloader import FixturesLoader

__all__ = ["RuleEnforcerTestCase", "RuleEnforcerDataTransformationTestCase"]

FIXTURES_1 = {
    "runners": ["testrunner1.yaml", "testrunner2.yaml"],
    "actions": ["action1.yaml", "a2.yaml", "a2_default_value.yaml"],
    "triggertypes": ["triggertype1.yaml"],
    "triggers": ["trigger1.yaml"],
    "traces": [
        "trace_for_test_enforce.yaml",
        "trace_for_test_enforce_2.yaml",
        "trace_for_test_enforce_3.yaml",
    ],
}
FIXTURES_2 = {
    "rules": [
        "rule1.yaml",
        "rule2.yaml",
        "rule_use_none_filter.yaml",
        "rule_none_no_use_none_filter.yaml",
        "rule_action_default_value.yaml",
        "rule_action_default_value_overridden.yaml",
        "rule_action_default_value_render_fail.yaml",
    ]
}

MOCK_TRIGGER_INSTANCE = TriggerInstanceDB()
MOCK_TRIGGER_INSTANCE.id = "triggerinstance-test"
MOCK_TRIGGER_INSTANCE.payload = {"t1_p": "t1_p_v"}
MOCK_TRIGGER_INSTANCE.occurrence_time = date_utils.get_datetime_utc_now()

MOCK_TRIGGER_INSTANCE_2 = TriggerInstanceDB()
MOCK_TRIGGER_INSTANCE_2.id = "triggerinstance-test2"
MOCK_TRIGGER_INSTANCE_2.payload = {"t1_p": None}
MOCK_TRIGGER_INSTANCE_2.occurrence_time = date_utils.get_datetime_utc_now()

MOCK_TRIGGER_INSTANCE_3 = TriggerInstanceDB()
MOCK_TRIGGER_INSTANCE_3.id = "triggerinstance-test3"
MOCK_TRIGGER_INSTANCE_3.payload = {"t1_p": None, "t2_p": "value2"}
MOCK_TRIGGER_INSTANCE_3.occurrence_time = date_utils.get_datetime_utc_now()

MOCK_TRIGGER_INSTANCE_PAYLOAD = {
    "k1": "v1",
    "k2": "v2",
    "k3": 3,
    "k4": True,
    "k5": {"foo": "bar"},
    "k6": [1, 3],
}

MOCK_TRIGGER_INSTANCE_4 = TriggerInstanceDB()
MOCK_TRIGGER_INSTANCE_4.id = "triggerinstance-test4"
MOCK_TRIGGER_INSTANCE_4.payload = MOCK_TRIGGER_INSTANCE_PAYLOAD
MOCK_TRIGGER_INSTANCE_4.occurrence_time = date_utils.get_datetime_utc_now()

MOCK_LIVEACTION = LiveActionDB()
MOCK_LIVEACTION.id = "liveaction-test-1.id"
MOCK_LIVEACTION.status = "requested"

MOCK_EXECUTION = ActionExecutionDB()
MOCK_EXECUTION.id = "exec-test-1.id"
MOCK_EXECUTION.status = "requested"

FAILURE_REASON = "fail!"


class BaseRuleEnforcerTestCase(DbTestCase):

    models = None

    @classmethod
    def setUpClass(cls):
        super(BaseRuleEnforcerTestCase, cls).setUpClass()

        runners_registrar.register_runners()

        # Create TriggerTypes before creation of Rule to avoid failure. Rule requires the
        # Trigger and therefore TriggerType to be created prior to rule creation.
        cls.models = FixturesLoader().save_fixtures_to_db(
            fixtures_pack=PACK, fixtures_dict=FIXTURES_1
        )
        cls.models.update(
            FixturesLoader().save_fixtures_to_db(
                fixtures_pack=PACK, fixtures_dict=FIXTURES_2
            )
        )
        MOCK_TRIGGER_INSTANCE.trigger = reference.get_ref_from_model(
            cls.models["triggers"]["trigger1.yaml"]
        )

    def setUp(self):
        super(BaseRuleEnforcerTestCase, self).setUp()

        MOCK_TRIGGER_INSTANCE_4.payload = MOCK_TRIGGER_INSTANCE_PAYLOAD


class RuleEnforcerTestCase(BaseRuleEnforcerTestCase):
    @mock.patch.object(
        action_service,
        "request",
        mock.MagicMock(return_value=(MOCK_LIVEACTION, MOCK_EXECUTION)),
    )
    def test_ruleenforcement_occurs(self):
        enforcer = RuleEnforcer(
            MOCK_TRIGGER_INSTANCE, self.models["rules"]["rule1.yaml"]
        )
        execution_db = enforcer.enforce()
        self.assertIsNotNone(execution_db)

    @mock.patch.object(
        action_service,
        "request",
        mock.MagicMock(return_value=(MOCK_LIVEACTION, MOCK_EXECUTION)),
    )
    def test_ruleenforcement_casts(self):
        enforcer = RuleEnforcer(
            MOCK_TRIGGER_INSTANCE, self.models["rules"]["rule2.yaml"]
        )
        execution_db = enforcer.enforce()
        self.assertIsNotNone(execution_db)
        self.assertTrue(action_service.request.called)
        self.assertIsInstance(
            action_service.request.call_args[0][0].parameters["objtype"], dict
        )

    @mock.patch.object(
        action_service,
        "request",
        mock.MagicMock(return_value=(MOCK_LIVEACTION, MOCK_EXECUTION)),
    )
    @mock.patch.object(RuleEnforcement, "add_or_update", mock.MagicMock())
    def test_ruleenforcement_create_on_success(self):
        enforcer = RuleEnforcer(
            MOCK_TRIGGER_INSTANCE, self.models["rules"]["rule2.yaml"]
        )
        execution_db = enforcer.enforce()
        self.assertIsNotNone(execution_db)
        self.assertTrue(RuleEnforcement.add_or_update.called)
        self.assertEqual(
            RuleEnforcement.add_or_update.call_args[0][0].rule.ref,
            self.models["rules"]["rule2.yaml"].ref,
        )
        self.assertEqual(
            RuleEnforcement.add_or_update.call_args[0][0].status,
            RULE_ENFORCEMENT_STATUS_SUCCEEDED,
        )

    @mock.patch.object(
        action_service,
        "request",
        mock.MagicMock(return_value=(MOCK_LIVEACTION, MOCK_EXECUTION)),
    )
    @mock.patch.object(RuleEnforcement, "add_or_update", mock.MagicMock())
    def test_rule_enforcement_create_rule_none_param_casting(self):
        mock_trigger_instance = MOCK_TRIGGER_INSTANCE_2

        # 1. Non None value, should be serialized as regular string
        mock_trigger_instance.payload = {"t1_p": "somevalue"}

        def mock_cast_string(x):
            assert x == "somevalue"
            return casts._cast_string(x)

        casts.CASTS["string"] = mock_cast_string

        enforcer = RuleEnforcer(
            mock_trigger_instance, self.models["rules"]["rule_use_none_filter.yaml"]
        )
        execution_db = enforcer.enforce()

        # Verify value has been serialized correctly
        call_args = action_service.request.call_args[0]
        live_action_db = call_args[0]
        self.assertEqual(live_action_db.parameters["actionstr"], "somevalue")
        self.assertIsNotNone(execution_db)
        self.assertTrue(RuleEnforcement.add_or_update.called)
        self.assertEqual(
            RuleEnforcement.add_or_update.call_args[0][0].rule.ref,
            self.models["rules"]["rule_use_none_filter.yaml"].ref,
        )
        self.assertEqual(
            RuleEnforcement.add_or_update.call_args[0][0].status,
            RULE_ENFORCEMENT_STATUS_SUCCEEDED,
        )

        # 2. Verify that None type from trigger instance is correctly serialized to
        # None when using "use_none" Jinja filter when invoking an action
        mock_trigger_instance.payload = {"t1_p": None}

        def mock_cast_string(x):
            assert x == data.NONE_MAGIC_VALUE
            return casts._cast_string(x)

        casts.CASTS["string"] = mock_cast_string

        enforcer = RuleEnforcer(
            mock_trigger_instance, self.models["rules"]["rule_use_none_filter.yaml"]
        )
        execution_db = enforcer.enforce()

        # Verify None has been correctly serialized to None
        call_args = action_service.request.call_args[0]
        live_action_db = call_args[0]
        self.assertEqual(live_action_db.parameters["actionstr"], None)
        self.assertIsNotNone(execution_db)
        self.assertTrue(RuleEnforcement.add_or_update.called)
        self.assertEqual(
            RuleEnforcement.add_or_update.call_args[0][0].rule.ref,
            self.models["rules"]["rule_use_none_filter.yaml"].ref,
        )
        self.assertEqual(
            RuleEnforcement.add_or_update.call_args[0][0].status,
            RULE_ENFORCEMENT_STATUS_SUCCEEDED,
        )

        casts.CASTS["string"] = casts._cast_string

        # 3. Parameter value is a compound string one of which values is None, but "use_none"
        # filter is not used
        mock_trigger_instance = MOCK_TRIGGER_INSTANCE_3
        mock_trigger_instance.payload = {"t1_p": None, "t2_p": "value2"}

        enforcer = RuleEnforcer(
            mock_trigger_instance,
            self.models["rules"]["rule_none_no_use_none_filter.yaml"],
        )
        execution_db = enforcer.enforce()

        # Verify None has been correctly serialized to None
        call_args = action_service.request.call_args[0]
        live_action_db = call_args[0]
        self.assertEqual(live_action_db.parameters["actionstr"], "None-value2")
        self.assertIsNotNone(execution_db)
        self.assertTrue(RuleEnforcement.add_or_update.called)
        self.assertEqual(
            RuleEnforcement.add_or_update.call_args[0][0].rule.ref,
            self.models["rules"]["rule_none_no_use_none_filter.yaml"].ref,
        )
        self.assertEqual(
            RuleEnforcement.add_or_update.call_args[0][0].status,
            RULE_ENFORCEMENT_STATUS_SUCCEEDED,
        )

        casts.CASTS["string"] = casts._cast_string

    @mock.patch.object(
        action_service,
        "request",
        mock.MagicMock(side_effect=ValueError(FAILURE_REASON)),
    )
    @mock.patch.object(RuleEnforcement, "add_or_update", mock.MagicMock())
    def test_ruleenforcement_create_on_fail(self):
        enforcer = RuleEnforcer(
            MOCK_TRIGGER_INSTANCE, self.models["rules"]["rule1.yaml"]
        )
        execution_db = enforcer.enforce()
        self.assertIsNone(execution_db)
        self.assertTrue(RuleEnforcement.add_or_update.called)
        self.assertEqual(
            RuleEnforcement.add_or_update.call_args[0][0].failure_reason, FAILURE_REASON
        )
        self.assertEqual(
            RuleEnforcement.add_or_update.call_args[0][0].status,
            RULE_ENFORCEMENT_STATUS_FAILED,
        )

    @mock.patch.object(
        action_service,
        "request",
        mock.MagicMock(return_value=(MOCK_LIVEACTION, MOCK_EXECUTION)),
    )
    @mock.patch.object(RuleEnforcement, "add_or_update", mock.MagicMock())
    @mock.patch(
        "st2common.util.param.get_config",
        mock.Mock(return_value={"arrtype_value": ["one 1", "two 2", "three 3"]}),
    )
    def test_action_default_jinja_parameter_value_is_rendered(self):
        # Verify that a default action parameter which is a Jinja variable is correctly rendered
        rule = self.models["rules"]["rule_action_default_value.yaml"]

        enforcer = RuleEnforcer(MOCK_TRIGGER_INSTANCE, rule)
        execution_db = enforcer.enforce()

        self.assertIsNotNone(execution_db)
        self.assertTrue(RuleEnforcement.add_or_update.called)
        self.assertEqual(
            RuleEnforcement.add_or_update.call_args[0][0].rule.ref, rule.ref
        )
        self.assertEqual(
            RuleEnforcement.add_or_update.call_args[0][0].status,
            RULE_ENFORCEMENT_STATUS_SUCCEEDED,
        )

        call_parameters = action_service.request.call_args[0][0].parameters

        self.assertEqual(call_parameters["objtype"], {"t1_p": "t1_p_v"})
        self.assertEqual(call_parameters["strtype"], "t1_p_v")
        self.assertEqual(call_parameters["arrtype"], ["one 1", "two 2", "three 3"])

    @mock.patch.object(
        action_service,
        "request",
        mock.MagicMock(return_value=(MOCK_LIVEACTION, MOCK_EXECUTION)),
    )
    @mock.patch.object(RuleEnforcement, "add_or_update", mock.MagicMock())
    def test_action_default_jinja_parameter_value_overridden_in_rule(self):
        # Verify that it works correctly if default parameter value is overridden in rule
        rule = self.models["rules"]["rule_action_default_value_overridden.yaml"]

        enforcer = RuleEnforcer(MOCK_TRIGGER_INSTANCE, rule)
        execution_db = enforcer.enforce()

        self.assertIsNotNone(execution_db)
        self.assertTrue(RuleEnforcement.add_or_update.called)
        self.assertEqual(
            RuleEnforcement.add_or_update.call_args[0][0].rule.ref, rule.ref
        )
        self.assertEqual(
            RuleEnforcement.add_or_update.call_args[0][0].status,
            RULE_ENFORCEMENT_STATUS_SUCCEEDED,
        )

        call_parameters = action_service.request.call_args[0][0].parameters

        self.assertEqual(call_parameters["objtype"], {"t1_p": "t1_p_v"})
        self.assertEqual(call_parameters["strtype"], "t1_p_v")
        self.assertEqual(call_parameters["arrtype"], ["override 1", "override 2"])

    @mock.patch.object(
        action_service,
        "request",
        mock.MagicMock(return_value=(MOCK_LIVEACTION, MOCK_EXECUTION)),
    )
    @mock.patch.object(
        action_service,
        "create_request",
        mock.MagicMock(return_value=(MOCK_LIVEACTION, MOCK_EXECUTION)),
    )
    @mock.patch.object(
        action_service,
        "update_status",
        mock.MagicMock(return_value=(MOCK_LIVEACTION, MOCK_EXECUTION)),
    )
    @mock.patch.object(RuleEnforcement, "add_or_update", mock.MagicMock())
    def test_action_default_jinja_parameter_value_render_fail(self):
        # Action parameter render failure should result in a failed execution
        rule = self.models["rules"]["rule_action_default_value_render_fail.yaml"]

        enforcer = RuleEnforcer(MOCK_TRIGGER_INSTANCE, rule)
        execution_db = enforcer.enforce()

        self.assertIsNone(execution_db)
        self.assertTrue(RuleEnforcement.add_or_update.called)
        self.assertEqual(
            RuleEnforcement.add_or_update.call_args[0][0].rule.ref, rule.ref
        )
        self.assertEqual(
            RuleEnforcement.add_or_update.call_args[0][0].status,
            RULE_ENFORCEMENT_STATUS_FAILED,
        )
        self.assertFalse(action_service.request.called)

        self.assertTrue(action_service.create_request.called)
        self.assertEqual(
            action_service.create_request.call_args[0][0].action,
            "wolfpack.a2_default_value",
        )

        self.assertTrue(action_service.update_status.called)
        self.assertEqual(
            action_service.update_status.call_args[1]["new_status"],
            action_constants.LIVEACTION_STATUS_FAILED,
        )

        expected_msg = (
            "Failed to render parameter \"arrtype\": 'dict object' has no "
            "attribute 'arrtype_value'"
        )

        result = action_service.update_status.call_args[1]["result"]
        self.assertEqual(result["error"], expected_msg)

        self.assertEqual(
            RuleEnforcement.add_or_update.call_args[0][0].failure_reason, expected_msg
        )


class RuleEnforcerDataTransformationTestCase(BaseRuleEnforcerTestCase):
    def test_payload_data_transform(self):
        rule = self.models["rules"]["rule_action_default_value_render_fail.yaml"]

        params = {"ip1": "{{trigger.k1}}-static", "ip2": "{{trigger.k2}} static"}

        expected_params = {"ip1": "v1-static", "ip2": "v2 static"}

        self.assertResolvedParamsMatchExpected(
            rule=rule,
            trigger_instance=MOCK_TRIGGER_INSTANCE_4,
            params=params,
            expected_params=expected_params,
        )

    def test_payload_transforms_int_type(self):
        rule = self.models["rules"]["rule_action_default_value_render_fail.yaml"]

        params = {"int": 666}
        expected_params = {"int": 666}

        self.assertResolvedParamsMatchExpected(
            rule=rule,
            trigger_instance=MOCK_TRIGGER_INSTANCE_4,
            params=params,
            expected_params=expected_params,
        )

    def test_payload_transforms_bool_type(self):
        rule = self.models["rules"]["rule_action_default_value_render_fail.yaml"]

        runner_type_db = mock.Mock()
        runner_type_db.runner_parameters = {}
        action_db = mock.Mock()
        action_db.parameters = {}

        params = {"bool": True}
        expected_params = {"bool": True}

        self.assertResolvedParamsMatchExpected(
            rule=rule,
            trigger_instance=MOCK_TRIGGER_INSTANCE_4,
            params=params,
            expected_params=expected_params,
        )

    def test_payload_transforms_complex_type(self):
        rule = self.models["rules"]["rule_action_default_value_render_fail.yaml"]

        runner_type_db = mock.Mock()
        runner_type_db.runner_parameters = {}
        action_db = mock.Mock()
        action_db.parameters = {}

        params = {
            "complex_dict": {"bool": True, "int": 666, "str": "{{trigger.k1}}-string"}
        }
        expected_params = {
            "complex_dict": {"bool": True, "int": 666, "str": "v1-string"}
        }

        self.assertResolvedParamsMatchExpected(
            rule=rule,
            trigger_instance=MOCK_TRIGGER_INSTANCE_4,
            params=params,
            expected_params=expected_params,
        )

        params = {"simple_list": [1, 2, 3]}
        expected_params = {"simple_list": [1, 2, 3]}

        self.assertResolvedParamsMatchExpected(
            rule=rule,
            trigger_instance=MOCK_TRIGGER_INSTANCE_4,
            params=params,
            expected_params=expected_params,
        )

    def test_hypenated_payload_transform(self):
        rule = self.models["rules"]["rule_action_default_value_render_fail.yaml"]
        payload = {"headers": {"hypenated-header": "dont-care"}, "k2": "v2"}

        MOCK_TRIGGER_INSTANCE_4.payload = payload
        params = {
            "ip1": "{{trigger.headers['hypenated-header']}}-static",
            "ip2": "{{trigger.k2}} static",
        }
        expected_params = {"ip1": "dont-care-static", "ip2": "v2 static"}

        self.assertResolvedParamsMatchExpected(
            rule=rule,
            trigger_instance=MOCK_TRIGGER_INSTANCE_4,
            params=params,
            expected_params=expected_params,
        )

    def test_system_transform(self):
        rule = self.models["rules"]["rule_action_default_value_render_fail.yaml"]

        runner_type_db = mock.Mock()
        runner_type_db.runner_parameters = {}
        action_db = mock.Mock()
        action_db.parameters = {}

        k5 = KeyValuePair.add_or_update(KeyValuePairDB(name="k5", value="v5"))
        k6 = KeyValuePair.add_or_update(KeyValuePairDB(name="k6", value="v6"))
        k7 = KeyValuePair.add_or_update(KeyValuePairDB(name="k7", value="v7"))
        k8 = KeyValuePair.add_or_update(
            KeyValuePairDB(name="k8", value="v8", scope=FULL_SYSTEM_SCOPE)
        )

        params = {
            "ip5": "{{trigger.k2}}-static",
            "ip6": "{{st2kv.system.k6}}-static",
            "ip7": "{{st2kv.system.k7}}-static",
        }
        expected_params = {"ip5": "v2-static", "ip6": "v6-static", "ip7": "v7-static"}

        try:
            self.assertResolvedParamsMatchExpected(
                rule=rule,
                trigger_instance=MOCK_TRIGGER_INSTANCE_4,
                params=params,
                expected_params=expected_params,
            )
        finally:
            KeyValuePair.delete(k5)
            KeyValuePair.delete(k6)
            KeyValuePair.delete(k7)
            KeyValuePair.delete(k8)

    def assertResolvedParamsMatchExpected(
        self, rule, trigger_instance, params, expected_params
    ):
        runner_type_db = mock.Mock()
        runner_type_db.runner_parameters = {}
        action_db = mock.Mock()
        action_db.parameters = {}

        enforcer = RuleEnforcer(trigger_instance, rule)
        context, additional_contexts = enforcer.get_action_execution_context(
            action_db=action_db
        )

        resolved_params = enforcer.get_resolved_parameters(
            action_db=action_db,
            runnertype_db=runner_type_db,
            params=params,
            context=context,
            additional_contexts=additional_contexts,
        )
        self.assertEqual(resolved_params, expected_params)
