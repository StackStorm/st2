# -*- coding: utf-8 -*-
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

import six
import mock

from oslo_config import cfg
from st2common.constants.keyvalue import FULL_USER_SCOPE
from st2common.exceptions.param import ParamException
from st2common.models.system.common import ResourceReference
from st2common.models.db.liveaction import LiveActionDB
from st2common.models.db.keyvalue import KeyValuePairDB
from st2common.models.utils import action_param_utils
from st2common.persistence.keyvalue import KeyValuePair
from st2common.transport.publishers import PoolPublisher
from st2common.util import date as date_utils
from st2common.util import param as param_utils
from st2common.util.config_loader import get_config

from st2tests import DbTestCase
from st2tests.fixtures.generic.fixture import PACK_NAME as FIXTURES_PACK
from st2tests.fixturesloader import FixturesLoader


TEST_MODELS = {
    "actions": ["action_4_action_context_param.yaml", "action_system_default.yaml"],
    "runners": ["testrunner1.yaml"],
}

FIXTURES = FixturesLoader().load_models(
    fixtures_pack=FIXTURES_PACK, fixtures_dict=TEST_MODELS
)


@mock.patch.object(PoolPublisher, "publish", mock.MagicMock())
class ParamsUtilsTest(DbTestCase):
    action_db = FIXTURES["actions"]["action_4_action_context_param.yaml"]
    action_system_default_db = FIXTURES["actions"]["action_system_default.yaml"]
    runnertype_db = FIXTURES["runners"]["testrunner1.yaml"]

    def test_process_jinja_exception(self):

        action_context = {"api_user": "noob"}
        config = {}
        G = param_utils._create_graph(action_context, config)
        name = "a1"
        value = {"test": "http://someurl?value={{a"}
        param_utils._process(G, name, value)
        self.assertEquals(G.nodes.get(name, {}).get("value"), value)

    def test_process_jinja_template(self):

        action_context = {"api_user": "noob"}
        config = {}
        G = param_utils._create_graph(action_context, config)
        name = "a1"
        value = "http://someurl?value={{a}}"
        param_utils._process(G, name, value)
        self.assertEquals(G.nodes.get(name, {}).get("template"), value)

    def test_get_finalized_params(self):
        params = {
            "actionstr": "foo",
            "some_key_that_aint_exist_in_action_or_runner": "bar",
            "runnerint": 555,
            "runnerimmutable": "failed_override",
            "actionimmutable": "failed_override",
        }
        liveaction_db = self._get_liveaction_model(params)

        runner_params, action_params = param_utils.get_finalized_params(
            ParamsUtilsTest.runnertype_db.runner_parameters,
            ParamsUtilsTest.action_db.parameters,
            liveaction_db.parameters,
            liveaction_db.context,
        )

        # Asserts for runner params.
        # Assert that default values for runner params are resolved.
        self.assertEqual(runner_params.get("runnerstr"), "defaultfoo")
        # Assert that a runner param from action exec is picked up.
        self.assertEqual(runner_params.get("runnerint"), 555)
        # Assert that a runner param can be overridden by action param default.
        self.assertEqual(runner_params.get("runnerdummy"), "actiondummy")
        # Assert that a runner param default can be overridden by 'falsey' action param default,
        # (timeout: 0 case).
        self.assertEqual(runner_params.get("runnerdefaultint"), 0)
        # Assert that an immutable param cannot be overridden by action param or execution param.
        self.assertEqual(runner_params.get("runnerimmutable"), "runnerimmutable")

        # Asserts for action params.
        self.assertEqual(action_params.get("actionstr"), "foo")
        # Assert that a param that is provided in action exec that isn't in action or runner params
        # isn't in resolved params.
        self.assertEqual(
            action_params.get("some_key_that_aint_exist_in_action_or_runner"), None
        )
        # Assert that an immutable param cannot be overridden by execution param.
        self.assertEqual(action_params.get("actionimmutable"), "actionimmutable")
        # Assert that an action context param is set correctly.
        self.assertEqual(action_params.get("action_api_user"), "noob")
        # Assert that none of runner params are present in action_params.
        for k in action_params:
            self.assertNotIn(k, runner_params, "Param " + k + " is a runner param.")

    def test_get_finalized_params_system_values(self):
        KeyValuePair.add_or_update(KeyValuePairDB(name="actionstr", value="foo"))
        KeyValuePair.add_or_update(KeyValuePairDB(name="actionnumber", value="1.0"))
        params = {"runnerint": 555}
        liveaction_db = self._get_liveaction_model(params)

        runner_params, action_params = param_utils.get_finalized_params(
            ParamsUtilsTest.runnertype_db.runner_parameters,
            ParamsUtilsTest.action_system_default_db.parameters,
            liveaction_db.parameters,
            liveaction_db.context,
        )

        # Asserts for runner params.
        # Assert that default values for runner params are resolved.
        self.assertEqual(runner_params.get("runnerstr"), "defaultfoo")
        # Assert that a runner param from action exec is picked up.
        self.assertEqual(runner_params.get("runnerint"), 555)
        # Assert that an immutable param cannot be overridden by action param or execution param.
        self.assertEqual(runner_params.get("runnerimmutable"), "runnerimmutable")

        # Asserts for action params.
        self.assertEqual(action_params.get("actionstr"), "foo")
        self.assertEqual(action_params.get("actionnumber"), 1.0)

    def test_get_finalized_params_action_immutable(self):
        params = {
            "actionstr": "foo",
            "some_key_that_aint_exist_in_action_or_runner": "bar",
            "runnerint": 555,
            "actionimmutable": "failed_override",
        }
        liveaction_db = self._get_liveaction_model(params)
        action_context = {"api_user": None}

        runner_params, action_params = param_utils.get_finalized_params(
            ParamsUtilsTest.runnertype_db.runner_parameters,
            ParamsUtilsTest.action_db.parameters,
            liveaction_db.parameters,
            action_context,
        )

        # Asserts for runner params.
        # Assert that default values for runner params are resolved.
        self.assertEqual(runner_params.get("runnerstr"), "defaultfoo")
        # Assert that a runner param from action exec is picked up.
        self.assertEqual(runner_params.get("runnerint"), 555)
        # Assert that a runner param can be overridden by action param default.
        self.assertEqual(runner_params.get("runnerdummy"), "actiondummy")

        # Asserts for action params.
        self.assertEqual(action_params.get("actionstr"), "foo")
        # Assert that a param that is provided in action exec that isn't in action or runner params
        # isn't in resolved params.
        self.assertEqual(
            action_params.get("some_key_that_aint_exist_in_action_or_runner"), None
        )

    def test_get_finalized_params_empty(self):
        params = {}
        runner_param_info = {}
        action_param_info = {}
        action_context = {"user": None}
        r_runner_params, r_action_params = param_utils.get_finalized_params(
            runner_param_info, action_param_info, params, action_context
        )
        self.assertEqual(r_runner_params, params)
        self.assertEqual(r_action_params, params)

    def test_get_finalized_params_none(self):
        params = {"r1": None, "a1": None}
        runner_param_info = {"r1": {}}
        action_param_info = {"a1": {}}
        action_context = {"api_user": None}
        r_runner_params, r_action_params = param_utils.get_finalized_params(
            runner_param_info, action_param_info, params, action_context
        )
        self.assertEqual(r_runner_params, {"r1": None})
        self.assertEqual(r_action_params, {"a1": None})

    def test_get_finalized_params_no_cast(self):
        params = {
            "r1": "{{r2}}",
            "r2": 1,
            "a1": True,
            "a2": "{{r1}} {{a1}}",
            "a3": "{{action_context.api_user}}",
        }
        runner_param_info = {"r1": {}, "r2": {}}
        action_param_info = {"a1": {}, "a2": {}, "a3": {}}
        action_context = {"api_user": "noob"}
        r_runner_params, r_action_params = param_utils.get_finalized_params(
            runner_param_info, action_param_info, params, action_context
        )
        self.assertEqual(r_runner_params, {"r1": "1", "r2": 1})
        self.assertEqual(r_action_params, {"a1": True, "a2": "1 True", "a3": "noob"})

    def test_get_finalized_params_with_cast(self):
        # Note : In this test runner_params.r1 has a string value. However per runner_param_info the
        # type is an integer. The expected type is considered and cast is performed accordingly.
        params = {
            "r1": "{{r2}}",
            "r2": 1,
            "a1": True,
            "a2": "{{a1}}",
            "a3": "{{action_context.api_user}}",
        }
        runner_param_info = {"r1": {"type": "integer"}, "r2": {"type": "integer"}}
        action_param_info = {
            "a1": {"type": "boolean"},
            "a2": {"type": "boolean"},
            "a3": {},
        }
        action_context = {"api_user": "noob"}
        r_runner_params, r_action_params = param_utils.get_finalized_params(
            runner_param_info, action_param_info, params, action_context
        )
        self.assertEqual(r_runner_params, {"r1": 1, "r2": 1})
        self.assertEqual(r_action_params, {"a1": True, "a2": True, "a3": "noob"})

    def test_get_finalized_params_with_cast_overriden(self):
        params = {
            "r1": "{{r2}}",
            "r2": 1,
            "a1": "{{r1}}",
            "a2": "{{r1}}",
            "a3": "{{r1}}",
        }
        runner_param_info = {"r1": {"type": "integer"}, "r2": {"type": "integer"}}
        action_param_info = {
            "a1": {"type": "boolean"},
            "a2": {"type": "string"},
            "a3": {"type": "integer"},
            "r1": {"type": "string"},
        }
        action_context = {"api_user": "noob"}
        r_runner_params, r_action_params = param_utils.get_finalized_params(
            runner_param_info, action_param_info, params, action_context
        )
        self.assertEqual(r_runner_params, {"r1": 1, "r2": 1})
        self.assertEqual(r_action_params, {"a1": 1, "a2": "1", "a3": 1})

    def test_get_finalized_params_cross_talk_no_cast(self):
        params = {
            "r1": "{{a1}}",
            "r2": 1,
            "a1": True,
            "a2": "{{r1}} {{a1}}",
            "a3": "{{action_context.api_user}}",
        }
        runner_param_info = {"r1": {}, "r2": {}}
        action_param_info = {"a1": {}, "a2": {}, "a3": {}}
        action_context = {"api_user": "noob"}
        r_runner_params, r_action_params = param_utils.get_finalized_params(
            runner_param_info, action_param_info, params, action_context
        )
        self.assertEqual(r_runner_params, {"r1": "True", "r2": 1})
        self.assertEqual(r_action_params, {"a1": True, "a2": "True True", "a3": "noob"})

    def test_get_finalized_params_cross_talk_with_cast(self):
        params = {
            "r1": "{{a1}}",
            "r2": 1,
            "r3": 1,
            "a1": True,
            "a2": "{{r1}},{{a1}},{{a3}},{{r3}}",
            "a3": "{{a1}}",
        }
        runner_param_info = {
            "r1": {"type": "boolean"},
            "r2": {"type": "integer"},
            "r3": {},
        }
        action_param_info = {
            "a1": {"type": "boolean"},
            "a2": {"type": "array"},
            "a3": {},
        }
        action_context = {"user": None}
        r_runner_params, r_action_params = param_utils.get_finalized_params(
            runner_param_info, action_param_info, params, action_context
        )
        self.assertEqual(r_runner_params, {"r1": True, "r2": 1, "r3": 1})
        self.assertEqual(
            r_action_params, {"a1": True, "a2": (True, True, True, 1), "a3": "True"}
        )

    def test_get_finalized_params_order(self):
        params = {"r1": "p1", "r2": "p2", "r3": "p3", "a1": "p4", "a2": "p5"}
        runner_param_info = {"r1": {}, "r2": {"default": "r2"}, "r3": {"default": "r3"}}
        action_param_info = {"a1": {}, "a2": {"default": "a2"}, "r3": {"default": "a3"}}
        action_context = {"api_user": "noob"}
        r_runner_params, r_action_params = param_utils.get_finalized_params(
            runner_param_info, action_param_info, params, action_context
        )
        self.assertEqual(r_runner_params, {"r1": "p1", "r2": "p2", "r3": "p3"})
        self.assertEqual(r_action_params, {"a1": "p4", "a2": "p5"})

        params = {}
        runner_param_info = {"r1": {}, "r2": {"default": "r2"}, "r3": {"default": "r3"}}
        action_param_info = {"a1": {}, "a2": {"default": "a2"}, "r3": {"default": "a3"}}
        action_context = {"api_user": "noob"}
        r_runner_params, r_action_params = param_utils.get_finalized_params(
            runner_param_info, action_param_info, params, action_context
        )
        self.assertEqual(r_runner_params, {"r1": None, "r2": "r2", "r3": "a3"})
        self.assertEqual(r_action_params, {"a1": None, "a2": "a2"})

        params = {}
        runner_param_info = {"r1": {}, "r2": {"default": "r2"}, "r3": {}}
        action_param_info = {"r1": {}, "r2": {}, "r3": {"default": "a3"}}
        action_context = {"api_user": "noob"}
        r_runner_params, r_action_params = param_utils.get_finalized_params(
            runner_param_info, action_param_info, params, action_context
        )
        self.assertEqual(r_runner_params, {"r1": None, "r2": "r2", "r3": "a3"})

    def test_get_finalized_params_non_existent_template_key_in_action_context(self):
        params = {
            "r1": "foo",
            "r2": 2,
            "a1": "i love tests",
            "a2": "{{action_context.lorem_ipsum}}",
        }
        runner_param_info = {"r1": {"type": "string"}, "r2": {"type": "integer"}}
        action_param_info = {"a1": {"type": "string"}, "a2": {"type": "string"}}
        action_context = {"api_user": "noob", "source_channel": "reddit"}
        try:
            r_runner_params, r_action_params = param_utils.get_finalized_params(
                runner_param_info, action_param_info, params, action_context
            )
            self.fail(
                "This should have thrown because we are trying to deref a key in "
                + "action context that ain't exist."
            )
        except ParamException as e:
            error_msg = (
                "Failed to render parameter \"a2\": 'dict object' "
                + "has no attribute 'lorem_ipsum'"
            )
            self.assertIn(error_msg, six.text_type(e))
            pass

    def test_unicode_value_casting(self):
        rendered = {"a1": "unicode1 ٩(̾●̮̮̃̾•̃̾)۶ unicode2"}
        parameter_schemas = {"a1": {"type": "string"}}

        result = param_utils._cast_params(
            rendered=rendered, parameter_schemas=parameter_schemas
        )

        expected = {"a1": ("unicode1 ٩(̾●̮̮̃̾•̃̾)۶ unicode2")}

        self.assertEqual(result, expected)

    def test_get_finalized_params_with_casting_unicode_values(self):
        params = {"a1": "unicode1 ٩(̾●̮̮̃̾•̃̾)۶ unicode2"}

        runner_param_info = {}
        action_param_info = {"a1": {"type": "string"}}

        action_context = {"user": None}

        r_runner_params, r_action_params = param_utils.get_finalized_params(
            runner_param_info, action_param_info, params, action_context
        )

        expected_action_params = {"a1": ("unicode1 ٩(̾●̮̮̃̾•̃̾)۶ unicode2")}

        self.assertEqual(r_runner_params, {})
        self.assertEqual(r_action_params, expected_action_params)

    def test_get_finalized_params_with_dict(self):
        # Note : In this test runner_params.r1 has a string value. However per runner_param_info the
        # type is an integer. The expected type is considered and cast is performed accordingly.
        params = {
            "r1": "{{r2}}",
            "r2": {"r2.1": 1},
            "a1": True,
            "a2": "{{a1}}",
            "a3": {
                "test": "{{a1}}",
                "test1": "{{a4}}",
                "test2": "{{a5}}",
            },
            "a4": 3,
            "a5": ["1", "{{a1}}"],
        }
        runner_param_info = {"r1": {"type": "object"}, "r2": {"type": "object"}}
        action_param_info = {
            "a1": {
                "type": "boolean",
            },
            "a2": {
                "type": "boolean",
            },
            "a3": {
                "type": "object",
            },
            "a4": {
                "type": "integer",
            },
            "a5": {
                "type": "array",
            },
        }
        r_runner_params, r_action_params = param_utils.get_finalized_params(
            runner_param_info, action_param_info, params, {"user": None}
        )
        self.assertEqual(r_runner_params, {"r1": {"r2.1": 1}, "r2": {"r2.1": 1}})
        self.assertEqual(
            r_action_params,
            {
                "a1": True,
                "a2": True,
                "a3": {
                    "test": True,
                    "test1": 3,
                    "test2": ["1", True],
                },
                "a4": 3,
                "a5": ["1", True],
            },
        )

    def test_get_finalized_params_with_list(self):
        # Note : In this test runner_params.r1 has a string value. However per runner_param_info the
        # type is an integer. The expected type is considered and cast is performed accordingly.
        self.maxDiff = None
        params = {
            "r1": "{{r2}}",
            "r2": ["1", "2"],
            "a1": True,
            "a2": "Test",
            "a3": "Test2",
            "a4": "{{a1}}",
            "a5": ["{{a2}}", "{{a3}}"],
            "a6": [
                ["{{r2}}", "{{a2}}"],
                ["{{a3}}", "{{a1}}"],
                [
                    "{{a7}}",
                    "This should be rendered as a string {{a1}}",
                    "{{a1}} This, too, should be rendered as a string {{a1}}",
                ],
            ],
            "a7": 5,
        }
        runner_param_info = {"r1": {"type": "array"}, "r2": {"type": "array"}}
        action_param_info = {
            "a1": {"type": "boolean"},
            "a2": {"type": "string"},
            "a3": {"type": "string"},
            "a4": {"type": "boolean"},
            "a5": {"type": "array"},
            "a6": {"type": "array"},
            "a7": {"type": "integer"},
        }
        r_runner_params, r_action_params = param_utils.get_finalized_params(
            runner_param_info, action_param_info, params, {"user": None}
        )
        self.assertEqual(r_runner_params, {"r1": ["1", "2"], "r2": ["1", "2"]})
        self.assertEqual(
            r_action_params,
            {
                "a1": True,
                "a2": "Test",
                "a3": "Test2",
                "a4": True,
                "a5": ["Test", "Test2"],
                "a6": [
                    [["1", "2"], "Test"],
                    ["Test2", True],
                    [
                        5,
                        "This should be rendered as a string True",
                        "True This, too, should be rendered as a string True",
                    ],
                ],
                "a7": 5,
            },
        )

    def test_get_finalized_params_with_cyclic_dependency(self):
        params = {"r1": "{{r2}}", "r2": "{{r1}}"}
        runner_param_info = {"r1": {}, "r2": {}}
        action_param_info = {}
        test_pass = True
        try:
            param_utils.get_finalized_params(
                runner_param_info, action_param_info, params, {"user": None}
            )
            test_pass = False
        except ParamException as e:
            test_pass = six.text_type(e).find("Cyclic") == 0
        self.assertTrue(test_pass)

    def test_get_finalized_params_with_missing_dependency(self):
        params = {"r1": "{{r3}}", "r2": "{{r3}}"}
        runner_param_info = {"r1": {}, "r2": {}}
        action_param_info = {}
        test_pass = True
        try:
            param_utils.get_finalized_params(
                runner_param_info, action_param_info, params, {"user": None}
            )
            test_pass = False
        except ParamException as e:
            test_pass = six.text_type(e).find("Dependency") == 0
        self.assertTrue(test_pass)

        params = {}
        runner_param_info = {"r1": {"default": "{{r3}}"}, "r2": {"default": "{{r3}}"}}
        action_param_info = {}
        test_pass = True
        try:
            param_utils.get_finalized_params(
                runner_param_info, action_param_info, params, {"user": None}
            )
            test_pass = False
        except ParamException as e:
            test_pass = six.text_type(e).find("Dependency") == 0
        self.assertTrue(test_pass)

    def test_get_finalized_params_no_double_rendering(self):
        params = {"r1": "{{ action_context.h1 }}{{ action_context.h2 }}"}
        runner_param_info = {"r1": {}}
        action_param_info = {}
        action_context = {"h1": "{", "h2": "{ missing }}", "user": None}
        r_runner_params, r_action_params = param_utils.get_finalized_params(
            runner_param_info, action_param_info, params, action_context
        )
        self.assertEqual(r_runner_params, {"r1": "{{ missing }}"})
        self.assertEqual(r_action_params, {})

    def test_get_finalized_params_jinja_filters(self):
        params = {"cmd": 'echo {{"1.6.0" | version_bump_minor}}'}
        runner_param_info = {"r1": {}}
        action_param_info = {"cmd": {}}
        action_context = {"user": None}

        r_runner_params, r_action_params = param_utils.get_finalized_params(
            runner_param_info, action_param_info, params, action_context
        )

        self.assertEqual(r_action_params["cmd"], "echo 1.7.0")

    def test_get_finalized_params_param_rendering_failure(self):
        params = {"cmd": "{{a2.foo}}", "a2": "test"}
        action_param_info = {"cmd": {}, "a2": {}}

        expected_msg = 'Failed to render parameter "cmd": .*'
        self.assertRaisesRegex(
            ParamException,
            expected_msg,
            param_utils.get_finalized_params,
            runnertype_parameter_info={},
            action_parameter_info=action_param_info,
            liveaction_parameters=params,
            action_context={"user": None},
        )

    def test_get_finalized_param_object_contains_template_notation_in_the_value(self):
        runner_param_info = {"r1": {}}
        action_param_info = {
            "params": {
                "type": "object",
                "default": {"host": "{{host}}", "port": "{{port}}", "path": "/bar"},
            }
        }
        params = {"host": "lolcathost", "port": 5555}
        action_context = {"user": None}

        r_runner_params, r_action_params = param_utils.get_finalized_params(
            runner_param_info, action_param_info, params, action_context
        )

        expected_params = {"host": "lolcathost", "port": 5555, "path": "/bar"}
        self.assertEqual(r_action_params["params"], expected_params)

    def test_cast_param_referenced_action_doesnt_exist(self):
        # Make sure the function throws if the action doesnt exist
        expected_msg = 'Action with ref "foo.doesntexist" doesn\'t exist'
        self.assertRaisesRegex(
            ValueError,
            expected_msg,
            action_param_utils.cast_params,
            action_ref="foo.doesntexist",
            params={},
        )

    def test_get_finalized_params_with_config(self):
        with mock.patch(
            "st2common.util.config_loader.ContentPackConfigLoader"
        ) as config_loader:
            config_loader().get_config.return_value = {
                "generic_config_param": "So generic"
            }

            params = {
                "config_param": "{{config_context.generic_config_param}}",
            }
            liveaction_db = self._get_liveaction_model(params, True)

            _, action_params = param_utils.get_finalized_params(
                ParamsUtilsTest.runnertype_db.runner_parameters,
                ParamsUtilsTest.action_db.parameters,
                liveaction_db.parameters,
                liveaction_db.context,
            )
            self.assertEqual(action_params.get("config_param"), "So generic")

    def test_get_config(self):
        with mock.patch(
            "st2common.util.config_loader.ContentPackConfigLoader"
        ) as config_loader:
            mock_config_return = {"generic_config_param": "So generic"}

            config_loader().get_config.return_value = mock_config_return

            self.assertEqual(get_config(None, None), {})
            self.assertEqual(get_config("pack", None), {})
            self.assertEqual(get_config(None, "user"), {})
            self.assertEqual(get_config("pack", "user"), mock_config_return)

            config_loader.assert_called_with(pack_name="pack", user="user")
            config_loader().get_config.assert_called_once()

    def _get_liveaction_model(self, params, with_config_context=False):
        status = "initializing"
        start_timestamp = date_utils.get_datetime_utc_now()
        action_ref = ResourceReference(
            name=ParamsUtilsTest.action_db.name, pack=ParamsUtilsTest.action_db.pack
        ).ref
        liveaction_db = LiveActionDB(
            status=status,
            start_timestamp=start_timestamp,
            action=action_ref,
            parameters=params,
        )
        liveaction_db.context = {
            "api_user": "noob",
            "source_channel": "reddit",
        }

        if with_config_context:
            liveaction_db.context.update({"pack": "generic", "user": "st2admin"})

        return liveaction_db

    def test_get_value_from_datastore_through_render_live_params(self):
        # Register datastore value to be refered by this test-case
        register_kwargs = [
            {"name": "test_key", "value": "foo"},
            {"name": "user1:test_key", "value": "bar", "scope": FULL_USER_SCOPE},
            {
                "name": "%s:test_key" % cfg.CONF.system_user.user,
                "value": "baz",
                "scope": FULL_USER_SCOPE,
            },
        ]
        for kwargs in register_kwargs:
            KeyValuePair.add_or_update(KeyValuePairDB(**kwargs))

        # Assert that datastore value can be got via the Jinja expression from individual scopes.
        context = {"user": "user1"}
        param = {
            "system_value": {"default": "{{ st2kv.system.test_key }}"},
            "user_value": {"default": "{{ st2kv.user.test_key }}"},
        }
        live_params = param_utils.render_live_params(
            runner_parameters={},
            action_parameters=param,
            params={},
            action_context=context,
        )

        self.assertEqual(live_params["system_value"], "foo")
        self.assertEqual(live_params["user_value"], "bar")

        # Assert that datastore value in the user-scope that is registered by user1
        # cannot be got by the operation of user2.
        context = {"user": "user2"}
        param = {"user_value": {"default": "{{ st2kv.user.test_key }}"}}
        live_params = param_utils.render_live_params(
            runner_parameters={},
            action_parameters=param,
            params={},
            action_context=context,
        )

        self.assertEqual(live_params["user_value"], "")

        # Assert that system-user's scope is selected when user and api_user parameter specified
        context = {}
        param = {"user_value": {"default": "{{ st2kv.user.test_key }}"}}
        live_params = param_utils.render_live_params(
            runner_parameters={},
            action_parameters=param,
            params={},
            action_context=context,
        )

        self.assertEqual(live_params["user_value"], "baz")

    def test_get_live_params_with_additional_context(self):
        runner_param_info = {"r1": {"default": "some"}}
        action_param_info = {"r2": {"default": "{{ r1 }}"}}
        params = {"r3": "lolcathost", "r1": "{{ additional.stuff }}"}
        action_context = {"user": None}
        additional_contexts = {"additional": {"stuff": "generic"}}

        live_params = param_utils.render_live_params(
            runner_param_info,
            action_param_info,
            params,
            action_context,
            additional_contexts,
        )

        expected_params = {"r1": "generic", "r2": "generic", "r3": "lolcathost"}
        self.assertEqual(live_params, expected_params)

    def test_cyclic_dependency_friendly_error_message(self):
        runner_param_info = {
            "r1": {
                "default": "some",
                "cyclic": "cyclic value",
                "morecyclic": "cyclic value",
            }
        }
        action_param_info = {"r2": {"default": "{{ r1 }}"}}
        params = {
            "r3": "lolcathost",
            "cyclic": "{{ cyclic }}",
            "morecyclic": "{{ morecyclic }}",
        }
        action_context = {"user": None}

        expected_msg = (
            "Cyclic dependency found in the following variables: cyclic, morecyclic"
        )
        self.assertRaisesRegex(
            ParamException,
            expected_msg,
            param_utils.render_live_params,
            runner_param_info,
            action_param_info,
            params,
            action_context,
        )

    def test_unsatisfied_dependency_friendly_error_message(self):
        runner_param_info = {
            "r1": {
                "default": "some",
            }
        }
        action_param_info = {"r2": {"default": "{{ r1 }}"}}
        params = {
            "r3": "lolcathost",
            "r4": "{{ variable_not_defined }}",
        }
        action_context = {"user": None}

        expected_msg = 'Dependency unsatisfied in variable "variable_not_defined"'
        self.assertRaisesRegex(
            ParamException,
            expected_msg,
            param_utils.render_live_params,
            runner_param_info,
            action_param_info,
            params,
            action_context,
        )

    def test_add_default_templates_to_live_params(self):
        """Test addition of template values in defaults to live params"""

        # Ensure parameter is skipped if the parameter has immutable set to true in schema
        schemas = [
            {
                "templateparam": {
                    "default": "{{ 3 | int }}",
                    "type": "integer",
                    "immutable": True,
                }
            }
        ]
        context = {"templateparam": "3"}
        result = param_utils._cast_params_from({}, context, schemas)
        self.assertEqual(result, {})

        # Test with no live params, and two parameters - one should make it through because
        # it was a template, and the other shouldn't because its default wasn't a template
        schemas = [{"templateparam": {"default": "{{ 3 | int }}", "type": "integer"}}]
        context = {"templateparam": "3"}
        result = param_utils._cast_params_from({}, context, schemas)
        self.assertEqual(result, {"templateparam": 3})

        # Ensure parameter is skipped if the value in context is identical to default
        schemas = [{"nottemplateparam": {"default": "4", "type": "integer"}}]
        context = {
            "nottemplateparam": "4",
        }
        result = param_utils._cast_params_from({}, context, schemas)
        self.assertEqual(result, {})

        # Ensure parameter is skipped if the parameter doesn't have a default
        schemas = [{"nottemplateparam": {"type": "integer"}}]
        context = {
            "nottemplateparam": "4",
        }
        result = param_utils._cast_params_from({}, context, schemas)
        self.assertEqual(result, {})

        # Skip if the default value isn't a Jinja expression
        schemas = [{"nottemplateparam": {"default": "5", "type": "integer"}}]
        context = {
            "nottemplateparam": "4",
        }
        result = param_utils._cast_params_from({}, context, schemas)
        self.assertEqual(result, {})

        # Ensure parameter is skipped if the parameter is being overridden
        schemas = [{"templateparam": {"default": "{{ 3 | int }}", "type": "integer"}}]
        context = {
            "templateparam": "4",
        }
        result = param_utils._cast_params_from({"templateparam": "4"}, context, schemas)
        self.assertEqual(result, {"templateparam": 4})

    def test_render_final_params_and_shell_script_action_command_strings(self):
        runner_parameters = {}
        action_db_parameters = {
            "project": {
                "type": "string",
                "default": "st2",
                "position": 0,
            },
            "version": {"type": "string", "position": 1, "required": True},
            "fork": {
                "type": "string",
                "position": 2,
                "default": "StackStorm",
            },
            "branch": {
                "type": "string",
                "position": 3,
                "default": "master",
            },
            "update_changelog": {"type": "boolean", "position": 4, "default": False},
            "local_repo": {
                "type": "string",
                "position": 5,
            },
        }
        context = {}

        # 1. All default values used
        live_action_db_parameters = {
            "project": "st2flow",
            "version": "3.0.0",
            "fork": "StackStorm",
            "local_repo": "/tmp/repo",
        }

        runner_params, action_params = param_utils.render_final_params(
            runner_parameters, action_db_parameters, live_action_db_parameters, context
        )

        self.assertDictEqual(
            action_params,
            {
                "project": "st2flow",
                "version": "3.0.0",
                "fork": "StackStorm",
                "branch": "master",  # default value used
                "update_changelog": False,  # default value used
                "local_repo": "/tmp/repo",
            },
        )

        # 2. Some default values used
        live_action_db_parameters = {
            "project": "st2web",
            "version": "3.1.0",
            "fork": "StackStorm1",
            "update_changelog": True,
            "local_repo": "/tmp/repob",
        }

        runner_params, action_params = param_utils.render_final_params(
            runner_parameters, action_db_parameters, live_action_db_parameters, context
        )

        self.assertDictEqual(
            action_params,
            {
                "project": "st2web",
                "version": "3.1.0",
                "fork": "StackStorm1",
                "branch": "master",  # default value used
                "update_changelog": True,  # default value used
                "local_repo": "/tmp/repob",
            },
        )

        # 3. None is specified for a boolean parameter, should use a default
        live_action_db_parameters = {
            "project": "st2rbac",
            "version": "3.2.0",
            "fork": "StackStorm2",
            "update_changelog": None,
            "local_repo": "/tmp/repoc",
        }

        runner_params, action_params = param_utils.render_final_params(
            runner_parameters, action_db_parameters, live_action_db_parameters, context
        )

        self.assertDictEqual(
            action_params,
            {
                "project": "st2rbac",
                "version": "3.2.0",
                "fork": "StackStorm2",
                "branch": "master",  # default value used
                "update_changelog": False,  # default value used
                "local_repo": "/tmp/repoc",
            },
        )
