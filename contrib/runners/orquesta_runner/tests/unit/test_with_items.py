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

from st2actions.workflows import workflows
from st2common.bootstrap import actionsregistrar
from st2common.bootstrap import runnersregistrar
from st2common.constants import action as action_constants
from st2common.models.api import inquiry as inqy_api_models
from st2common.models.db import liveaction as lv_db_models
from st2common.persistence import execution as ex_db_access
from st2common.persistence import liveaction as lv_db_access
from st2common.persistence import workflow as wf_db_access
from st2common.services import action as action_service
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
class OrquestaWithItemsTest(st2tests.DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(OrquestaWithItemsTest, cls).setUpClass()

        # Register runners.
        runnersregistrar.register_runners()

        # Register test pack(s).
        actions_registrar = actionsregistrar.ActionsRegistrar(
            use_pack_cache=False,
            fail_on_failure=True
        )

        for pack in PACKS:
            actions_registrar.register_from_pack(pack)

    @classmethod
    def get_runner_class(cls, runner_name):
        return runners.get_runner(runner_name, runner_name).__class__

    def test_with_items(self):
        num_items = 3

        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, 'with-items.yaml')
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = action_service.request(lv_ac_db)

        # Assert action execution is running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_RUNNING)
        wf_ex_db = wf_db_access.WorkflowExecution.query(action_execution=str(ac_ex_db.id))[0]
        self.assertEqual(wf_ex_db.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Process the with items task.
        query_filters = {'workflow_execution': str(wf_ex_db.id), 'task_id': 'task1'}
        t1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t1_ac_ex_dbs = ex_db_access.ActionExecution.query(task_execution=str(t1_ex_db.id))

        self.assertEqual(len(t1_ac_ex_dbs), num_items)

        status = [
            ac_ex.status == action_constants.LIVEACTION_STATUS_SUCCEEDED
            for ac_ex in t1_ac_ex_dbs
        ]

        self.assertTrue(all(status))

        for t1_ac_ex_db in t1_ac_ex_dbs:
            workflows.get_engine().process(t1_ac_ex_db)

        t1_ex_db = wf_db_access.TaskExecution.get_by_id(t1_ex_db.id)
        self.assertEqual(t1_ex_db.status, wf_states.SUCCEEDED)

        # Assert the main workflow is completed.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_states.SUCCEEDED)

    def test_with_items_concurrency(self):
        num_items = 3
        concurrency = 2

        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, 'with-items-concurrency.yaml')
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = action_service.request(lv_ac_db)

        # Assert action execution is running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_RUNNING)
        wf_ex_db = wf_db_access.WorkflowExecution.query(action_execution=str(ac_ex_db.id))[0]
        self.assertEqual(wf_ex_db.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Process the first set of action executions from with items concurrency.
        query_filters = {'workflow_execution': str(wf_ex_db.id), 'task_id': 'task1'}
        t1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t1_ac_ex_dbs = ex_db_access.ActionExecution.query(task_execution=str(t1_ex_db.id))

        self.assertEqual(len(t1_ac_ex_dbs), concurrency)

        status = [
            ac_ex.status == action_constants.LIVEACTION_STATUS_SUCCEEDED
            for ac_ex in t1_ac_ex_dbs
        ]

        self.assertTrue(all(status))

        for t1_ac_ex_db in t1_ac_ex_dbs:
            workflows.get_engine().process(t1_ac_ex_db)

        t1_ex_db = wf_db_access.TaskExecution.get_by_id(t1_ex_db.id)
        self.assertEqual(t1_ex_db.status, wf_states.RUNNING)

        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_states.RUNNING)

        # Process the second set of action executions from with items concurrency.
        t1_ac_ex_dbs = ex_db_access.ActionExecution.query(task_execution=str(t1_ex_db.id))

        self.assertEqual(len(t1_ac_ex_dbs), num_items)

        status = [
            ac_ex.status == action_constants.LIVEACTION_STATUS_SUCCEEDED
            for ac_ex in t1_ac_ex_dbs
        ]

        self.assertTrue(all(status))

        for t1_ac_ex_db in t1_ac_ex_dbs[concurrency:]:
            workflows.get_engine().process(t1_ac_ex_db)

        t1_ex_db = wf_db_access.TaskExecution.get_by_id(t1_ex_db.id)
        self.assertEqual(t1_ex_db.status, wf_states.SUCCEEDED)

        # Assert the main workflow is completed.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_states.SUCCEEDED)
