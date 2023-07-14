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

import copy
import mock

from oslo_config import cfg

from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED
from st2common.models.db.execution import ActionExecutionDB
from st2common.services import action as action_service
from st2tests.api import SUPER_SECRET_PARAMETER
from st2tests.fixtures.aliases.fixture import PACK_NAME as FIXTURES_PACK
from st2tests.fixturesloader import FixturesLoader
from st2tests.api import FunctionalTest

TEST_MODELS = {
    "aliases": [
        "alias1.yaml",
        "alias2.yaml",
        "alias_with_undefined_jinja_in_ack_format.yaml",
        "alias_with_immutable_list_param.yaml",
        "alias_with_immutable_list_param_str_cast.yaml",
        "alias4.yaml",
        "alias5.yaml",
        "alias_fixes1.yaml",
        "alias_fixes2.yaml",
        "alias_match_multiple.yaml",
    ],
    "actions": ["action1.yaml", "action2.yaml", "action3.yaml", "action4.yaml"],
    "runners": ["runner1.yaml"],
}

TEST_LOAD_MODELS = {"aliases": ["alias3.yaml"]}

EXECUTION = ActionExecutionDB(
    id="54e657d60640fd16887d6855", status=LIVEACTION_STATUS_SUCCEEDED, result={}
)

__all__ = ["AliasExecutionTestCase"]


class AliasExecutionTestCase(FunctionalTest):

    models = None
    alias1 = None
    alias2 = None
    alias_with_undefined_jinja_in_ack_format = None

    @classmethod
    def setUpClass(cls):
        super(AliasExecutionTestCase, cls).setUpClass()
        cls.models = FixturesLoader().save_fixtures_to_db(
            fixtures_pack=FIXTURES_PACK, fixtures_dict=TEST_MODELS
        )

        cls.runner1 = cls.models["runners"]["runner1.yaml"]
        cls.action1 = cls.models["actions"]["action1.yaml"]
        cls.alias1 = cls.models["aliases"]["alias1.yaml"]
        cls.alias2 = cls.models["aliases"]["alias2.yaml"]
        cls.alias4 = cls.models["aliases"]["alias4.yaml"]
        cls.alias5 = cls.models["aliases"]["alias5.yaml"]
        cls.alias_with_undefined_jinja_in_ack_format = cls.models["aliases"][
            "alias_with_undefined_jinja_in_ack_format.yaml"
        ]

    @mock.patch.object(action_service, "request", return_value=(None, EXECUTION))
    def test_basic_execution(self, request):
        command = 'Lorem ipsum value1 dolor sit "value2 value3" amet.'
        post_resp = self._do_post(alias_execution=self.alias1, command=command)
        self.assertEqual(post_resp.status_int, 201)
        expected_parameters = {"param1": "value1", "param2": "value2 value3"}
        self.assertEqual(request.call_args[0][0].parameters, expected_parameters)

    @mock.patch.object(action_service, "request", return_value=(None, EXECUTION))
    def test_basic_execution_with_immutable_parameters(self, request):
        command = "lorem ipsum"
        post_resp = self._do_post(alias_execution=self.alias5, command=command)
        self.assertEqual(post_resp.status_int, 201)
        expected_parameters = {"param1": "value1", "param2": "value2"}
        self.assertEqual(request.call_args[0][0].parameters, expected_parameters)

    @mock.patch.object(action_service, "request", return_value=(None, EXECUTION))
    def test_invalid_format_string_referenced_in_request(self, request):
        command = 'Lorem ipsum value1 dolor sit "value2 value3" amet.'
        format_str = "some invalid not supported string"
        post_resp = self._do_post(
            alias_execution=self.alias1,
            command=command,
            format_str=format_str,
            expect_errors=True,
        )
        self.assertEqual(post_resp.status_int, 400)
        expected_msg = (
            'Format string "some invalid not supported string" is '
            'not available on the alias "alias1"'
        )
        self.assertIn(expected_msg, post_resp.json["faultstring"])

    @mock.patch.object(action_service, "request", return_value=(None, EXECUTION))
    def test_execution_with_array_type_single_value(self, request):
        command = "Lorem ipsum value1 dolor sit value2 amet."
        self._do_post(alias_execution=self.alias2, command=command)
        expected_parameters = {"param1": "value1", "param3": ["value2"]}
        self.assertEqual(request.call_args[0][0].parameters, expected_parameters)

    @mock.patch.object(action_service, "request", return_value=(None, EXECUTION))
    def test_execution_with_array_type_multi_value(self, request):
        command = 'Lorem ipsum value1 dolor sit "value2, value3" amet.'
        post_resp = self._do_post(alias_execution=self.alias2, command=command)
        self.assertEqual(post_resp.status_int, 201)
        expected_parameters = {"param1": "value1", "param3": ["value2", "value3"]}
        self.assertEqual(request.call_args[0][0].parameters, expected_parameters)

    @mock.patch.object(action_service, "request", return_value=(None, EXECUTION))
    def test_invalid_jinja_var_in_ack_format(self, request):
        command = "run date on localhost"
        # print(self.alias_with_undefined_jinja_in_ack_format)
        post_resp = self._do_post(
            alias_execution=self.alias_with_undefined_jinja_in_ack_format,
            command=command,
            expect_errors=False,
        )
        self.assertEqual(post_resp.status_int, 201)
        expected_parameters = {"cmd": "date", "hosts": "localhost"}
        self.assertEqual(request.call_args[0][0].parameters, expected_parameters)
        self.assertEqual(
            post_resp.json["message"],
            'Cannot render "format" in field "ack" for alias. \'cmd\' is undefined',
        )

    @mock.patch.object(action_service, "request")
    def test_execution_secret_parameter(self, request):

        execution = ActionExecutionDB(
            id="54e657d60640fd16887d6855",
            status=LIVEACTION_STATUS_SUCCEEDED,
            action={"parameters": self.action1.parameters},
            runner={"runner_parameters": self.runner1.runner_parameters},
            parameters={"param4": SUPER_SECRET_PARAMETER},
            result={},
        )

        request.return_value = (None, execution)

        command = "Lorem ipsum value1 dolor sit " + SUPER_SECRET_PARAMETER + " amet."
        post_resp = self._do_post(alias_execution=self.alias4, command=command)
        self.assertEqual(post_resp.status_int, 201)
        expected_parameters = {"param1": "value1", "param4": SUPER_SECRET_PARAMETER}
        self.assertEqual(request.call_args[0][0].parameters, expected_parameters)
        post_resp = self._do_post(
            alias_execution=self.alias4,
            command=command,
            show_secrets=True,
            expect_errors=True,
        )
        self.assertEqual(post_resp.status_int, 201)
        self.assertEqual(
            post_resp.json["execution"]["parameters"]["param4"], SUPER_SECRET_PARAMETER
        )

    @mock.patch.object(action_service, "request", return_value=(None, EXECUTION))
    def test_match_and_execute_doesnt_match(self, mock_request):
        base_data = {
            "source_channel": "chat",
            "notification_route": "hubot",
            "user": "chat-user",
        }

        # Command doesnt match any patterns
        data = copy.deepcopy(base_data)
        data["command"] = "hello donny"
        resp = self.app.post_json(
            "/v1/aliasexecution/match_and_execute", data, expect_errors=True
        )
        self.assertEqual(resp.status_int, 400)
        self.assertEqual(
            str(resp.json["faultstring"]), "Command 'hello donny' matched no patterns"
        )

    @mock.patch.object(action_service, "request", return_value=(None, EXECUTION))
    def test_match_and_execute_matches_many(self, mock_request):
        base_data = {
            "source_channel": "chat",
            "notification_route": "hubot",
            "user": "chat-user",
        }

        # Command matches more than one pattern
        data = copy.deepcopy(base_data)
        data["command"] = "Lorem ipsum banana dolor sit pineapple amet."
        resp = self.app.post_json(
            "/v1/aliasexecution/match_and_execute", data, expect_errors=True
        )
        self.assertEqual(resp.status_int, 400)
        self.assertEqual(
            str(resp.json["faultstring"]),
            "Command 'Lorem ipsum banana dolor sit pineapple amet.' "
            "matched more than 1 pattern",
        )

    @mock.patch.object(action_service, "request", return_value=(None, EXECUTION))
    def test_match_and_execute_matches_one(self, mock_request):
        base_data = {
            "source_channel": "chat-channel",
            "notification_route": "hubot",
            "user": "chat-user",
        }

        # Command matches - should result in action execution
        data = copy.deepcopy(base_data)
        data["command"] = "run date on localhost"
        resp = self.app.post_json("/v1/aliasexecution/match_and_execute", data)
        self.assertEqual(resp.status_int, 201)
        self.assertEqual(len(resp.json["results"]), 1)
        self.assertEqual(
            resp.json["results"][0]["execution"]["id"], str(EXECUTION["id"])
        )
        self.assertEqual(
            resp.json["results"][0]["execution"]["status"], EXECUTION["status"]
        )

        expected_parameters = {"cmd": "date", "hosts": "localhost"}
        self.assertEqual(mock_request.call_args[0][0].parameters, expected_parameters)

        # Also check for source_channel - see
        # https://github.com/StackStorm/st2/issues/4650
        actual_context = mock_request.call_args[0][0].context

        self.assertIn("source_channel", mock_request.call_args[0][0].context.keys())
        self.assertEqual(actual_context["source_channel"], "chat-channel")
        self.assertEqual(actual_context["api_user"], "chat-user")
        self.assertEqual(actual_context["user"], cfg.CONF.system_user.user)

    @mock.patch.object(action_service, "request", return_value=(None, EXECUTION))
    def test_match_and_execute_matches_one_multiple_match(self, mock_request):
        base_data = {
            "source_channel": "chat",
            "notification_route": "hubot",
            "user": "chat-user",
        }

        # Command matches multiple times - should result in multiple action execution
        data = copy.deepcopy(base_data)
        data["command"] = (
            "JKROWLING-4 is a duplicate of JRRTOLKIEN-24 which "
            "is a duplicate of DRSEUSS-12"
        )
        resp = self.app.post_json("/v1/aliasexecution/match_and_execute", data)
        self.assertEqual(resp.status_int, 201)
        self.assertEqual(len(resp.json["results"]), 2)
        self.assertEqual(
            resp.json["results"][0]["execution"]["id"], str(EXECUTION["id"])
        )
        self.assertEqual(
            resp.json["results"][0]["execution"]["status"], EXECUTION["status"]
        )
        self.assertEqual(
            resp.json["results"][1]["execution"]["id"], str(EXECUTION["id"])
        )
        self.assertEqual(
            resp.json["results"][1]["execution"]["status"], EXECUTION["status"]
        )

        # The mock object only stores the parameters of the _last_ time it was called, so that's
        # what we assert on. Luckily re.finditer() processes groups in order, so if this was the
        # parameters to the mock object, we have _also_ called it with:
        #
        # {'issue_key': 'JRRTOLKIEN-24'}
        #
        # We've also already checked the results array
        #
        expected_parameters = {"issue_key": "DRSEUSS-12"}
        self.assertEqual(mock_request.call_args[0][0].parameters, expected_parameters)

    @mock.patch.object(action_service, "request", return_value=(None, EXECUTION))
    def test_match_and_execute_matches_many_multiple_match(self, mock_request):
        base_data = {
            "source_channel": "chat",
            "notification_route": "hubot",
            "user": "chat-user",
        }

        # Command matches multiple times - should result in multiple action execution
        data = copy.deepcopy(base_data)
        data["command"] = "JKROWLING-4 fixes JRRTOLKIEN-24 which fixes DRSEUSS-12"
        resp = self.app.post_json(
            "/v1/aliasexecution/match_and_execute", data, expect_errors=True
        )
        self.assertEqual(resp.status_int, 400)
        self.assertEqual(
            str(resp.json["faultstring"]),
            "Command '{command}' "
            "matched more than 1 (multi) pattern".format(command=data["command"]),
        )

    def test_match_and_execute_list_action_param_str_cast_to_list(self):
        data = {
            "command": "test alias list param str cast",
            "source_channel": "hubot",
            "user": "foo",
        }
        resp = self.app.post_json(
            "/v1/aliasexecution/match_and_execute", data, expect_errors=True
        )

        # Param is a comma delimited string - our custom cast function should cast it to a list.
        # I assume that was done to make specifying complex params in chat easier.
        # NOTE: This function only handles casting list, but not casting nested list items (e.g.
        # list of objects)
        self.assertEqual(resp.status_int, 201)

        result = resp.json["results"][0]
        live_action = result["execution"]["liveaction"]
        action_alias = result["actionalias"]

        self.assertEqual(resp.status_int, 201)
        self.assertTrue(isinstance(live_action["parameters"]["array_param"], list))
        self.assertEqual(live_action["parameters"]["array_param"][0], "one")
        self.assertEqual(live_action["parameters"]["array_param"][1], "two")
        self.assertEqual(live_action["parameters"]["array_param"][2], "three")
        self.assertEqual(live_action["parameters"]["array_param"][3], "four")
        self.assertTrue(
            isinstance(action_alias["immutable_parameters"]["array_param"], str)
        )

    def test_match_and_execute_list_action_param_already_a_list(self):
        data = {
            "command": "test alias foo",
            "source_channel": "hubot",
            "user": "foo",
        }
        resp = self.app.post_json(
            "/v1/aliasexecution/match_and_execute", data, expect_errors=True
        )

        # immutable_param is already a list - verify no casting is performed
        self.assertEqual(resp.status_int, 201)

        result = resp.json["results"][0]
        live_action = result["execution"]["liveaction"]
        action_alias = result["actionalias"]

        self.assertEqual(resp.status_int, 201)
        self.assertTrue(isinstance(live_action["parameters"]["array_param"], list))
        self.assertEqual(live_action["parameters"]["array_param"][0]["key1"], "one")
        self.assertEqual(live_action["parameters"]["array_param"][0]["key2"], "two")
        self.assertEqual(live_action["parameters"]["array_param"][1]["key3"], "three")
        self.assertEqual(live_action["parameters"]["array_param"][1]["key4"], "four")
        self.assertTrue(
            isinstance(action_alias["immutable_parameters"]["array_param"], list)
        )

    def test_match_and_execute_success(self):
        data = {
            "command": "run whoami on localhost1",
            "source_channel": "hubot",
            "user": "user",
        }
        resp = self.app.post_json("/v1/aliasexecution/match_and_execute", data)
        self.assertEqual(resp.status_int, 201)
        self.assertEqual(len(resp.json["results"]), 1)
        self.assertTrue(
            resp.json["results"][0]["actionalias"]["ref"],
            "aliases.alias_with_undefined_jinja_in_ack_format",
        )

    def _do_post(
        self,
        alias_execution,
        command,
        format_str=None,
        expect_errors=False,
        show_secrets=False,
    ):
        if isinstance(alias_execution.formats[0], dict) and alias_execution.formats[
            0
        ].get("representation"):
            representation = alias_execution.formats[0].get("representation")[0]
        else:
            representation = alias_execution.formats[0]

        if not format_str:
            format_str = representation

        execution = {
            "name": alias_execution.name,
            "format": format_str,
            "command": command,
            "user": cfg.CONF.system_user.user,
            "source_channel": "test",
            "notification_route": "test",
        }
        url = (
            show_secrets
            and "/v1/aliasexecution?show_secrets=true"
            or "/v1/aliasexecution"
        )
        return self.app.post_json(url, execution, expect_errors=expect_errors)
