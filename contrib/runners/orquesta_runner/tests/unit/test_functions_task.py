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

from __future__ import absolute_import

import mock

from orquesta import states as wf_states

import st2tests

# XXX: actionsensor import depends on config being setup.
import st2tests.config as tests_config
tests_config.parse_args()

from tests.unit import base

from st2common.bootstrap import actionsregistrar
from st2common.bootstrap import runnersregistrar
from st2common.constants import action as ac_const
from st2common.models.db import liveaction as lv_db_models
from st2common.persistence import execution as ex_db_access
from st2common.persistence import liveaction as lv_db_access
from st2common.persistence import workflow as wf_db_access
from st2common.services import action as ac_svc
from st2common.services import workflows as wf_svc
from st2common.transport import liveaction as lv_ac_xport
from st2common.transport import workflow as wf_ex_xport
from st2common.transport import publishers
from st2tests.mocks import liveaction as mock_lv_ac_xport
from st2tests.mocks import workflow as mock_wf_ex_xport


TEST_PACK = 'orquesta_tests'
TEST_PACK_PATH = st2tests.fixturesloader.get_fixtures_packs_base_path() + '/' + TEST_PACK

PACKS = [
    TEST_PACK_PATH,
    st2tests.fixturesloader.get_fixtures_packs_base_path() + '/core'
]


@mock.patch.object(
    publishers.CUDPublisher,
    'publish_update',
    mock.MagicMock(return_value=None))
@mock.patch.object(
    lv_ac_xport.LiveActionPublisher,
    'publish_create',
    mock.MagicMock(side_effect=mock_lv_ac_xport.MockLiveActionPublisher.publish_create))
@mock.patch.object(
    lv_ac_xport.LiveActionPublisher,
    'publish_state',
    mock.MagicMock(side_effect=mock_lv_ac_xport.MockLiveActionPublisher.publish_state))
@mock.patch.object(
    wf_ex_xport.WorkflowExecutionPublisher,
    'publish_create',
    mock.MagicMock(side_effect=mock_wf_ex_xport.MockWorkflowExecutionPublisher.publish_create))
@mock.patch.object(
    wf_ex_xport.WorkflowExecutionPublisher,
    'publish_state',
    mock.MagicMock(side_effect=mock_wf_ex_xport.MockWorkflowExecutionPublisher.publish_state))
class OrquestaFunctionTest(st2tests.DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(OrquestaFunctionTest, cls).setUpClass()

        # Register runners.
        runnersregistrar.register_runners()

        # Register test pack(s).
        actions_registrar = actionsregistrar.ActionsRegistrar(
            use_pack_cache=False,
            fail_on_failure=True
        )

        for pack in PACKS:
            actions_registrar.register_from_pack(pack)

    def _execute_workflow(self, wf_name, expected_task_sequence, expected_output,
                          expected_status=wf_states.SUCCEEDED, expected_errors=None):
        wf_file = wf_name + '.yaml'
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, wf_file)
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)

        # Assert action execution is running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING, lv_ac_db.result)
        wf_ex_db = wf_db_access.WorkflowExecution.query(action_execution=str(ac_ex_db.id))[0]
        self.assertEqual(wf_ex_db.status, ac_const.LIVEACTION_STATUS_RUNNING)

        for task_id in expected_task_sequence:
            query_filters = {'workflow_execution': str(wf_ex_db.id), 'task_id': task_id}
            tk_ex_dbs = wf_db_access.TaskExecution.query(**query_filters)
            tk_ex_db = sorted(tk_ex_dbs, key=lambda x: x.start_timestamp)[len(tk_ex_dbs) - 1]
            tk_ac_ex_db = ex_db_access.ActionExecution.query(task_execution=str(tk_ex_db.id))[0]
            tk_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk_ac_ex_db.liveaction['id'])
            self.assertEqual(tk_lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
            self.assertTrue(wf_svc.is_action_execution_under_workflow_context(tk_ac_ex_db))
            wf_svc.handle_action_execution_completion(tk_ac_ex_db)

        # Assert workflow is completed.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, expected_status)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, expected_status)
        ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db.id))
        self.assertEqual(ac_ex_db.status, expected_status)

        # Check workflow output, liveaction result, and action execution result.
        expected_result = {'output': expected_output}

        if expected_errors is not None:
            expected_result['errors'] = expected_errors

        if expected_output is not None:
            self.assertDictEqual(wf_ex_db.output, expected_output)

        self.assertDictEqual(lv_ac_db.result, expected_result)
        self.assertDictEqual(ac_ex_db.result, expected_result)

    def test_task_functions_in_yaql(self):
        wf_name = 'yaql-task-functions'

        expected_task_sequence = [
            'task1',
            'task2',
            'task3',
            'task3',
            'task4',
            'task5',
            'task6',
            'task7__1',
            'task7__2',
            'task8__1',
            'task8__2'
        ]

        expected_output = {
            'last_task3_result': True,
            'task8__1__parent': 'task7__1',
            'task8__2__parent': 'task7__2',
            'that_task_by_name': 'task1',
            'this_task_by_name': 'task1',
            'this_task_no_arg': 'task1'
        }

        self._execute_workflow(wf_name, expected_task_sequence, expected_output)

    def test_task_functions_in_jinja(self):
        wf_name = 'jinja-task-functions'

        expected_task_sequence = [
            'task1',
            'task2',
            'task3',
            'task3',
            'task4',
            'task5',
            'task6',
            'task7__1',
            'task7__2',
            'task8__1',
            'task8__2'
        ]

        expected_output = {
            'last_task3_result': True,
            'task8__1__parent': 'task7__1',
            'task8__2__parent': 'task7__2',
            'that_task_by_name': 'task1',
            'this_task_by_name': 'task1',
            'this_task_no_arg': 'task1'
        }

        self._execute_workflow(wf_name, expected_task_sequence, expected_output)

    def test_task_nonexistent_in_yaql(self):
        wf_name = 'yaql-task-nonexistent'

        expected_task_sequence = ['task1']

        expected_output = None

        expected_errors = [
            {
                'message': 'Unable to find task execution for "task0".',
                'task_transition_id': 'noop__0',
                'task_id': 'task1'
            }
        ]

        self._execute_workflow(
            wf_name,
            expected_task_sequence,
            expected_output,
            expected_status=ac_const.LIVEACTION_STATUS_FAILED,
            expected_errors=expected_errors
        )

    def test_task_nonexistent_in_jinja(self):
        wf_name = 'jinja-task-nonexistent'

        expected_task_sequence = ['task1']

        expected_output = None

        expected_errors = [
            {
                'message': 'Unable to find task execution for "task0".',
                'task_transition_id': 'noop__0',
                'task_id': 'task1'
            }
        ]

        self._execute_workflow(
            wf_name,
            expected_task_sequence,
            expected_output,
            expected_status=ac_const.LIVEACTION_STATUS_FAILED,
            expected_errors=expected_errors
        )
