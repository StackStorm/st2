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

import mock

from orquesta import statuses as wf_statuses

import st2tests

# XXX: actionsensor import depends on config being setup.
import st2tests.config as tests_config

tests_config.parse_args()

from tests.unit import base

from st2common.bootstrap import actionsregistrar
from st2common.bootstrap import runnersregistrar
from st2common.constants import action as ac_const
from st2common.expressions.functions import data as data_funcs
from st2common.models.db import liveaction as lv_db_models
from st2common.persistence import execution as ex_db_access
from st2common.persistence import liveaction as lv_db_access
from st2common.persistence import workflow as wf_db_access
from st2common.services import action as ac_svc
from st2common.services import workflows as wf_svc
from st2common.transport import liveaction as lv_ac_xport
from st2common.transport import workflow as wf_ex_xport
from st2common.transport import publishers
from st2tests.fixtures.packs.core.fixture import PACK_PATH as CORE_PACK_PATH
from st2tests.fixtures.packs.orquesta_tests.fixture import PACK_PATH as TEST_PACK_PATH
from st2tests.mocks import liveaction as mock_lv_ac_xport
from st2tests.mocks import workflow as mock_wf_ex_xport


PACKS = [TEST_PACK_PATH, CORE_PACK_PATH]


@mock.patch.object(
    publishers.CUDPublisher, "publish_update", mock.MagicMock(return_value=None)
)
@mock.patch.object(
    lv_ac_xport.LiveActionPublisher,
    "publish_create",
    mock.MagicMock(side_effect=mock_lv_ac_xport.MockLiveActionPublisher.publish_create),
)
@mock.patch.object(
    lv_ac_xport.LiveActionPublisher,
    "publish_state",
    mock.MagicMock(side_effect=mock_lv_ac_xport.MockLiveActionPublisher.publish_state),
)
@mock.patch.object(
    wf_ex_xport.WorkflowExecutionPublisher,
    "publish_create",
    mock.MagicMock(
        side_effect=mock_wf_ex_xport.MockWorkflowExecutionPublisher.publish_create
    ),
)
@mock.patch.object(
    wf_ex_xport.WorkflowExecutionPublisher,
    "publish_state",
    mock.MagicMock(
        side_effect=mock_wf_ex_xport.MockWorkflowExecutionPublisher.publish_state
    ),
)
class OrquestaFunctionTest(st2tests.ExecutionDbTestCase):
    @classmethod
    def setUpClass(cls):
        super(OrquestaFunctionTest, cls).setUpClass()

        # Register runners.
        runnersregistrar.register_runners()

        # Register test pack(s).
        actions_registrar = actionsregistrar.ActionsRegistrar(
            use_pack_cache=False, fail_on_failure=True
        )

        for pack in PACKS:
            actions_registrar.register_from_pack(pack)

    def _execute_workflow(self, wf_name, expected_output):
        wf_file = wf_name + ".yaml"
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, wf_file)
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)

        # Assert action execution is running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(
            lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING, lv_ac_db.result
        )
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]
        self.assertEqual(wf_ex_db.status, ac_const.LIVEACTION_STATUS_RUNNING)

        # Assert task1 is already completed.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task1"}
        tk1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk1_ex_db.id)
        )[0]
        tk1_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk1_ac_ex_db.liveaction["id"])
        self.assertEqual(tk1_lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        self.assertTrue(wf_svc.is_action_execution_under_workflow_context(tk1_ac_ex_db))

        # Manually handle action execution completion.
        wf_svc.handle_action_execution_completion(tk1_ac_ex_db)

        # Assert workflow is completed.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.SUCCEEDED)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db.id))
        self.assertEqual(ac_ex_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # Check workflow output, liveaction result, and action execution result.
        expected_result = {"output": expected_output}
        self.assertDictEqual(wf_ex_db.output, expected_output)
        self.assertDictEqual(lv_ac_db.result, expected_result)
        self.assertDictEqual(ac_ex_db.result, expected_result)

    def test_data_functions_in_yaql(self):
        wf_name = "yaql-data-functions"

        expected_output = {
            "data_json_str_1": '{"foo": {"bar": "foobar"}}',
            "data_json_str_2": '{"foo": {"bar": "foobar"}}',
            "data_json_str_3": '{"foo": {"bar": "foobar"}}',
            "data_json_obj_1": {"foo": {"bar": "foobar"}},
            "data_json_obj_2": {"foo": {"bar": "foobar"}},
            "data_json_obj_3": {"foo": {"bar": "foobar"}},
            "data_json_obj_4": {"foo": {"bar": "foobar"}},
            "data_yaml_str_1": "foo:\n  bar: foobar\n",
            "data_yaml_str_2": "foo:\n  bar: foobar\n",
            "data_query_1": ["foobar"],
            "data_none_str": data_funcs.NONE_MAGIC_VALUE,
            "data_str": "foobar",
        }

        self._execute_workflow(wf_name, expected_output)

    def test_data_functions_in_jinja(self):
        wf_name = "jinja-data-functions"

        expected_output = {
            "data_json_str_1": '{"foo": {"bar": "foobar"}}',
            "data_json_str_2": '{"foo": {"bar": "foobar"}}',
            "data_json_str_3": '{"foo": {"bar": "foobar"}}',
            "data_json_obj_1": {"foo": {"bar": "foobar"}},
            "data_json_obj_2": {"foo": {"bar": "foobar"}},
            "data_json_obj_3": {"foo": {"bar": "foobar"}},
            "data_json_obj_4": {"foo": {"bar": "foobar"}},
            "data_yaml_str_1": "foo:\n  bar: foobar\n",
            "data_yaml_str_2": "foo:\n  bar: foobar\n",
            "data_query_1": ["foobar"],
            "data_pipe_str_1": '{"foo": {"bar": "foobar"}}',
            "data_none_str": data_funcs.NONE_MAGIC_VALUE,
            "data_str": "foobar",
            "data_list_str": "- a: 1\n  b: 2\n- x: 3\n  y: 4\n",
        }

        self._execute_workflow(wf_name, expected_output)

    def test_path_functions_in_yaql(self):
        wf_name = "yaql-path-functions"

        expected_output = {"basename": "file.txt", "dirname": "/path/to/some"}

        self._execute_workflow(wf_name, expected_output)

    def test_path_functions_in_jinja(self):
        wf_name = "jinja-path-functions"

        expected_output = {"basename": "file.txt", "dirname": "/path/to/some"}

        self._execute_workflow(wf_name, expected_output)

    def test_regex_functions_in_yaql(self):
        wf_name = "yaql-regex-functions"

        expected_output = {
            "match": True,
            "replace": "wxyz",
            "search": True,
            "substring": "668 Infinite Dr",
        }

        self._execute_workflow(wf_name, expected_output)

    def test_regex_functions_in_jinja(self):
        wf_name = "jinja-regex-functions"

        expected_output = {
            "match": True,
            "replace": "wxyz",
            "search": True,
            "substring": "668 Infinite Dr",
        }

        self._execute_workflow(wf_name, expected_output)

    def test_time_functions_in_yaql(self):
        wf_name = "yaql-time-functions"

        expected_output = {"time": "3h25m45s"}

        self._execute_workflow(wf_name, expected_output)

    def test_time_functions_in_jinja(self):
        wf_name = "jinja-time-functions"

        expected_output = {"time": "3h25m45s"}

        self._execute_workflow(wf_name, expected_output)

    def test_version_functions_in_yaql(self):
        wf_name = "yaql-version-functions"

        expected_output = {
            "compare_equal": 0,
            "compare_more_than": -1,
            "compare_less_than": 1,
            "equal": True,
            "more_than": False,
            "less_than": False,
            "match": True,
            "bump_major": "1.0.0",
            "bump_minor": "0.11.0",
            "bump_patch": "0.10.1",
            "strip_patch": "0.10",
        }

        self._execute_workflow(wf_name, expected_output)

    def test_version_functions_in_jinja(self):
        wf_name = "jinja-version-functions"

        expected_output = {
            "compare_equal": 0,
            "compare_more_than": -1,
            "compare_less_than": 1,
            "equal": True,
            "more_than": False,
            "less_than": False,
            "match": True,
            "bump_major": "1.0.0",
            "bump_minor": "0.11.0",
            "bump_patch": "0.10.1",
            "strip_patch": "0.10",
        }

        self._execute_workflow(wf_name, expected_output)
