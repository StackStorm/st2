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
import uuid

import st2tests

import st2tests.config as tests_config
tests_config.parse_args()

from st2common.bootstrap import actionsregistrar
from st2common.bootstrap import runnersregistrar
from st2common.constants import action as ac_const
from st2common.models.db import liveaction as lv_db_models
from st2common.runners import base as runners
from st2common.services import action as ac_svc
from st2common.transport import liveaction as lv_ac_xport
from st2common.transport import publishers
from st2tests.mocks import liveaction as mock_lv_ac_xport


TEST_FIXTURES = {
    'workflows': [
        'rerun.yaml'
    ],
    'actions': [
        'rerun.yaml'
    ]
}

TEST_PACK = 'orquesta_tests'
TEST_PACK_PATH = st2tests.fixturesloader.get_fixtures_packs_base_path() + '/' + TEST_PACK

PACKS = [
    TEST_PACK_PATH,
    st2tests.fixturesloader.get_fixtures_packs_base_path() + '/core'
]

OPTIONS = {
    'tasks': ['task1']
}


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
class OrquestRunnerTest(st2tests.WorkflowTestCase, st2tests.ExecutionDbTestCase):

    @classmethod
    def setUpClass(cls):
        super(OrquestRunnerTest, cls).setUpClass()

        # Register runners.
        runnersregistrar.register_runners()

        # Register test pack(s).
        actions_registrar = actionsregistrar.ActionsRegistrar(
            use_pack_cache=False,
            fail_on_failure=True
        )

        for pack in PACKS:
            actions_registrar.register_from_pack(pack)

    @staticmethod
    def get_runner_class(runner_name):
        return runners.get_runner(runner_name).__class__

    def assert_raises_with_message(self, msg, func, *args, **kwargs):
        try:
            self.assertRaises(func, *args, **kwargs)
        except Exception as inst:
            self.assertEqual(inst.message, msg)

    def test_rerun_option(self):
        patched_orquesta_runner = self.get_runner_class('orquesta')

        mock_rerun_result = (
            ac_const.LIVEACTION_STATUS_RUNNING,
            {'tasks': []},
            {'execution_id': str(uuid.uuid4())}
        )

        with mock.patch.object(patched_orquesta_runner, 'rerun_workflow',
                               mock.MagicMock(return_value=mock_rerun_result)):

            wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, TEST_FIXTURES['workflows'][0])
            lv_ac_db1 = lv_db_models.LiveActionDB(action=wf_meta['name'])
            lv_ac_db1, ac_ex_db1 = ac_svc.request(lv_ac_db1)
            self.assertFalse(patched_orquesta_runner.rerun_workflow.called)

            # Rerun the execution.
            context = {
                're-run': {
                    'ref': ac_ex_db1.id,
                    'tasks': ['task1']
                }
            }

            lv_ac_db2 = lv_db_models.LiveActionDB(action=wf_meta['name'], context=context)
            lv_ac_db2, ac_ex_db2 = ac_svc.request(lv_ac_db2)

            self._wait_on_status(
                lv_ac_db2,
                ac_const.LIVEACTION_STATUS_RUNNING
            )

            options = {
                'ref': ac_ex_db1.id,
                'tasks': ['task1'],
            }
            patched_orquesta_runner.rerun_workflow.assert_called_with(ex_ref=ac_ex_db1,
                                                                      options=options)

    def test_rerun_with_invalid_workflow_id(self):
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, TEST_FIXTURES['workflows'][0])
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.create_request(lv_ac_db)

        # Rerun option.
        context = {
            're-run': OPTIONS
        }

        # At this point, workflow execution value is not assigned yet
        # and action execution status is requested
        self.assertEqual(ac_ex_db.workflow_execution, None)
        self.assertEqual(ac_ex_db.status, ac_const.LIVEACTION_STATUS_REQUESTED)

        # Manually setup workflow status to failed in order to test invalid workflow ID.
        ac_ex_db.status = ac_const.LIVEACTION_STATUS_FAILED

        orquesta_runner = self.get_runner_class('orquesta')
        self.assert_raises_with_message(
            'Unable to rerun because Orquesta workflow execution_id is missing.',
            Exception,
            orquesta_runner.rerun_workflow,
            ac_ex_db,
            context
        )

    def test_rerun_with_unrerunnable_status(self):
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, TEST_FIXTURES['workflows'][0])
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.create_request(lv_ac_db)

        # Rerun option.
        context = {
            're-run': OPTIONS
        }

        # At this point, workflow execution value is not assigned yet
        # and action execution status is requested
        self.assertEqual(ac_ex_db.workflow_execution, None)
        self.assertEqual(ac_ex_db.status, ac_const.LIVEACTION_STATUS_REQUESTED)

        # Manually setup workflow execution id in order to test unrerunnable status
        ac_ex_db.workflow_execution = '5cd31c9d076129256abd70c7'

        orquesta_runner = self.get_runner_class('orquesta')
        self.assert_raises_with_message(
            'Workflow execution is not in a rerunable state.',
            Exception,
            orquesta_runner.rerun_workflow,
            ac_ex_db,
            context
        )
