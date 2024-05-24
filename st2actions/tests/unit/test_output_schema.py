# Copyright 2021 The StackStorm Authors.
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

import mock

from http_runner import http_runner
from python_runner import python_runner
from orquesta_runner import orquesta_runner

# This import must be early for import-time side-effects.
import st2tests

from st2common.bootstrap import actionsregistrar
from st2common.bootstrap import runnersregistrar
from st2common.constants import action as ac_const
from st2common.constants import secrets as secrets_const
from st2common.models.api import execution as ex_api_models
from st2common.models.db import liveaction as lv_db_models
from st2common.services import action as action_service
from st2common.transport import liveaction as lv_ac_xport
from st2common.transport import publishers
from st2tests.mocks import liveaction as mock_lv_ac_xport

from st2tests.fixtures.packs.dummy_pack_1.fixture import PACK_PATH as DUMMY_PACK_1_PATH
from st2tests.fixtures.packs.orquesta_tests.fixture import (
    PACK_PATH as ORQUESTA_TESTS_PACK_PATH,
)


PACKS = [
    DUMMY_PACK_1_PATH,
    ORQUESTA_TESTS_PACK_PATH,
]

MOCK_PYTHON_ACTION_RESULT = {
    "stderr": "",
    "stdout": "",
    "result": {"k1": "foobar", "k2": "shhhh!"},
    "exit_code": 0,
}

MOCK_PYTHON_RUNNER_OUTPUT = (
    ac_const.LIVEACTION_STATUS_SUCCEEDED,
    MOCK_PYTHON_ACTION_RESULT,
    None,
)

MOCK_HTTP_ACTION_RESULT = {
    "status_code": 200,
    "body": {"k1": "foobar", "k2": "shhhh!"},
}

MOCK_HTTP_RUNNER_OUTPUT = (
    ac_const.LIVEACTION_STATUS_SUCCEEDED,
    MOCK_HTTP_ACTION_RESULT,
    None,
)

MOCK_ORQUESTA_ACTION_RESULT = {
    "errors": [],
    "output": {"a6": "foobar", "b6": "foobar", "a7": "foobar", "b7": "shhhh!"},
}

MOCK_ORQUESTA_RUNNER_OUTPUT = (
    ac_const.LIVEACTION_STATUS_SUCCEEDED,
    MOCK_ORQUESTA_ACTION_RESULT,
    None,
)


@mock.patch.object(
    publishers.CUDPublisher, "publish_update", mock.MagicMock(return_value=None)
)
@mock.patch.object(
    publishers.CUDPublisher,
    "publish_create",
    mock.MagicMock(side_effect=mock_lv_ac_xport.MockLiveActionPublisher.publish_create),
)
@mock.patch.object(
    lv_ac_xport.LiveActionPublisher,
    "publish_state",
    mock.MagicMock(side_effect=mock_lv_ac_xport.MockLiveActionPublisher.publish_state),
)
class ActionExecutionOutputSchemaTest(st2tests.ExecutionDbTestCase):
    @classmethod
    def setUpClass(cls):
        super(ActionExecutionOutputSchemaTest, cls).setUpClass()

        # Register runners.
        runnersregistrar.register_runners()

        # Register test pack(s).
        actions_registrar = actionsregistrar.ActionsRegistrar(
            use_pack_cache=False, fail_on_failure=True
        )

        for pack in PACKS:
            actions_registrar.register_from_pack(pack)

    @mock.patch.object(
        python_runner.PythonRunner,
        "run",
        mock.MagicMock(return_value=MOCK_PYTHON_RUNNER_OUTPUT),
    )
    def test_python_action(self):
        # Execute a python action with output schema and secret
        lv_ac_db = lv_db_models.LiveActionDB(action="dummy_pack_1.my_py_action")
        lv_ac_db, ac_ex_db = action_service.request(lv_ac_db)
        ac_ex_db = self._wait_on_ac_ex_status(
            ac_ex_db, ac_const.LIVEACTION_STATUS_SUCCEEDED
        )

        # Assert expected output written to the database
        expected_output = {"k1": "foobar", "k2": "shhhh!"}
        self.assertDictEqual(ac_ex_db.result["result"], expected_output)

        # Assert expected output on conversion to API model
        ac_ex_api = ex_api_models.ActionExecutionAPI.from_model(
            ac_ex_db, mask_secrets=True
        )
        expected_masked_output = {
            "k1": "foobar",
            "k2": secrets_const.MASKED_ATTRIBUTE_VALUE,
        }
        self.assertDictEqual(ac_ex_api.result["result"], expected_masked_output)

    @mock.patch.object(
        http_runner.HttpRunner,
        "run",
        mock.MagicMock(return_value=MOCK_HTTP_RUNNER_OUTPUT),
    )
    def test_http_action(self):
        # Execute a http action with output schema and secret
        lv_ac_db = lv_db_models.LiveActionDB(action="dummy_pack_1.my_http_action")
        lv_ac_db, ac_ex_db = action_service.request(lv_ac_db)
        ac_ex_db = self._wait_on_ac_ex_status(
            ac_ex_db, ac_const.LIVEACTION_STATUS_SUCCEEDED
        )

        # Assert expected output written to the database
        expected_output = {"k1": "foobar", "k2": "shhhh!"}
        self.assertDictEqual(ac_ex_db.result["body"], expected_output)

        # Assert expected output on conversion to API model
        ac_ex_api = ex_api_models.ActionExecutionAPI.from_model(
            ac_ex_db, mask_secrets=True
        )
        expected_masked_output = {
            "k1": "foobar",
            "k2": secrets_const.MASKED_ATTRIBUTE_VALUE,
        }
        self.assertDictEqual(ac_ex_api.result["body"], expected_masked_output)

    @mock.patch.object(
        orquesta_runner.OrquestaRunner,
        "run",
        mock.MagicMock(return_value=MOCK_ORQUESTA_RUNNER_OUTPUT),
    )
    def test_orquesta_action(self):
        wf_input = "foobar"

        # Execute an orquesta action with output schema and secret
        lv_ac_db = lv_db_models.LiveActionDB(
            action="orquesta_tests.data-flow", parameters={"a1": wf_input}
        )
        lv_ac_db, ac_ex_db = action_service.request(lv_ac_db)
        ac_ex_db = self._wait_on_ac_ex_status(
            ac_ex_db, ac_const.LIVEACTION_STATUS_SUCCEEDED
        )

        # Assert expected output written to the database
        expected_output = {
            "a6": wf_input,
            "b6": wf_input,
            "a7": wf_input,
            "b7": "shhhh!",
        }
        self.assertDictEqual(ac_ex_db.result["output"], expected_output)

        # Assert expected output on conversion to API model
        ac_ex_api = ex_api_models.ActionExecutionAPI.from_model(
            ac_ex_db, mask_secrets=True
        )
        expected_masked_output = {
            "a6": wf_input,
            "b6": wf_input,
            "a7": wf_input,
            "b7": secrets_const.MASKED_ATTRIBUTE_VALUE,
        }
        self.assertDictEqual(ac_ex_api.result["output"], expected_masked_output)
