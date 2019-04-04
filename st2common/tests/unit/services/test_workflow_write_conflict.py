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
import os
import tempfile

from orquesta import statuses as wf_statuses

import st2tests

import st2tests.config as tests_config
tests_config.parse_args()

from st2common.bootstrap import actionsregistrar
from st2common.bootstrap import runnersregistrar
from st2common.exceptions import db as db_exc
from st2common.models.db import liveaction as lv_db_models
from st2common.persistence import workflow as wf_db_access
from st2common.services import action as ac_svc
from st2common.services import workflows as wf_svc
from st2common.transport import liveaction as lv_ac_xport
from st2common.transport import publishers
from st2tests.mocks import liveaction as mock_lv_ac_xport


TEST_FIXTURES = {
    'workflows': [
        'join.yaml'
    ],
    'actions': [
        'join.yaml'
    ]
}

TEST_PACK = 'orquesta_tests'
TEST_PACK_PATH = st2tests.fixturesloader.get_fixtures_packs_base_path() + '/' + TEST_PACK

PACKS = [
    TEST_PACK_PATH,
    st2tests.fixturesloader.get_fixtures_packs_base_path() + '/core'
]

# Temporary directory used by the tests.
TEMP_DIR_PATH = tempfile.mkdtemp()


def mock_wf_db_update_conflict(wf_ex_db, publish=True, dispatch_trigger=True, **kwargs):
    seq_len = len(wf_ex_db.state['sequence'])

    if seq_len > 0:
        current_task_id = wf_ex_db.state['sequence'][seq_len - 1:][0]['id']
        temp_file_path = TEMP_DIR_PATH + '/' + current_task_id

        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            raise db_exc.StackStormDBObjectWriteConflictError(wf_ex_db)

    return wf_db_access.WorkflowExecution._get_impl().update(wf_ex_db, **kwargs)


@mock.patch.object(
    publishers.CUDPublisher,
    'publish_update',
    mock.MagicMock(return_value=None))
@mock.patch.object(
    publishers.CUDPublisher,
    'publish_create',
    mock.MagicMock(side_effect=mock_lv_ac_xport.MockLiveActionPublisher.publish_create))
@mock.patch.object(
    lv_ac_xport.LiveActionPublisher,
    'publish_state',
    mock.MagicMock(side_effect=mock_lv_ac_xport.MockLiveActionPublisher.publish_state))
class WorkflowExecutionWriteConflictTest(st2tests.WorkflowTestCase):

    @classmethod
    def setUpClass(cls):
        super(WorkflowExecutionWriteConflictTest, cls).setUpClass()

        # Register runners.
        runnersregistrar.register_runners()

        # Register test pack(s).
        actions_registrar = actionsregistrar.ActionsRegistrar(
            use_pack_cache=False,
            fail_on_failure=True
        )

        for pack in PACKS:
            actions_registrar.register_from_pack(pack)

    @mock.patch.object(
        wf_db_access.WorkflowExecution, 'update',
        mock.MagicMock(side_effect=mock_wf_db_update_conflict))
    def test_retry_on_write_conflict(self):
        # Create a temporary file which will be used to signal
        # which task(s) to mock the DB write conflict.
        temp_file_path = TEMP_DIR_PATH + '/task4'
        if not os.path.exists(temp_file_path):
            with open(temp_file_path, 'w'):
                pass

        # Manually create the liveaction and action execution objects without publishing.
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, TEST_FIXTURES['workflows'][0])
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.create_request(lv_ac_db)

        # Request and pre-process the workflow execution.
        wf_def = self.get_wf_def(TEST_PACK_PATH, wf_meta)
        st2_ctx = self.mock_st2_context(ac_ex_db)
        wf_ex_db = wf_svc.request(wf_def, ac_ex_db, st2_ctx)
        wf_ex_db = self.prep_wf_ex(wf_ex_db)

        # Manually request task executions.
        task_route = 0
        self.run_workflow_step(wf_ex_db, 'task1', task_route)
        self.assert_task_running('task2', task_route)
        self.assert_task_running('task4', task_route)
        self.run_workflow_step(wf_ex_db, 'task2', task_route)
        self.assert_task_running('task3', task_route)
        self.run_workflow_step(wf_ex_db, 'task4', task_route)
        self.assert_task_running('task5', task_route)
        self.run_workflow_step(wf_ex_db, 'task3', task_route)
        self.assert_task_not_started('task6', task_route)
        self.run_workflow_step(wf_ex_db, 'task5', task_route)
        self.assert_task_running('task6', task_route)
        self.run_workflow_step(wf_ex_db, 'task6', task_route)
        self.assert_task_running('task7', task_route)
        self.run_workflow_step(wf_ex_db, 'task7', task_route)
        self.assert_workflow_completed(str(wf_ex_db.id), status=wf_statuses.SUCCEEDED)

        # Ensure retry happened.
        self.assertFalse(os.path.exists(temp_file_path))
