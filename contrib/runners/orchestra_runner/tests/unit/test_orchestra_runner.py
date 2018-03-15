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

# XXX: actionsensor import depends on config being setup.
import st2tests.config as tests_config
tests_config.parse_args()

from tests.unit import base

from st2common.bootstrap import actionsregistrar
from st2common.bootstrap import runnersregistrar
from st2common.constants import action as action_constants
from st2common.models.db.liveaction import LiveActionDB
from st2common.persistence.liveaction import LiveAction
from st2common.persistence.workflow import WorkflowExecution
from st2common.runners import base as runners
from st2common.services import action as action_service
from st2common.transport.liveaction import LiveActionPublisher
from st2common.transport.publishers import CUDPublisher
from st2tests import DbTestCase
from st2tests import fixturesloader
from st2tests.mocks.liveaction import MockLiveActionPublisher


TEST_FIXTURES = {
    'workflows': [
        'sequential.yaml',
        'fail-inspection.yaml'
    ],
    'actions': [
        'sequential.yaml',
        'fail-inspection.yaml'
    ]
}

TEST_PACK = 'orchestra_tests'
TEST_PACK_PATH = fixturesloader.get_fixtures_packs_base_path() + '/' + TEST_PACK

PACKS = [
    TEST_PACK_PATH,
    fixturesloader.get_fixtures_packs_base_path() + '/core'
]


@mock.patch.object(
    CUDPublisher,
    'publish_update',
    mock.MagicMock(return_value=None))
@mock.patch.object(
    CUDPublisher,
    'publish_create',
    mock.MagicMock(side_effect=MockLiveActionPublisher.publish_create))
@mock.patch.object(
    LiveActionPublisher,
    'publish_state',
    mock.MagicMock(side_effect=MockLiveActionPublisher.publish_state))
class OrchestraRunnerTest(DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(OrchestraRunnerTest, cls).setUpClass()

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

    def test_launch_workflow(self):
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, TEST_FIXTURES['workflows'][0])
        liveaction = LiveActionDB(action=wf_meta['name'])
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))

        self.assertTrue(liveaction.action_is_workflow)
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_RUNNING)

        wf_exs = WorkflowExecution.query(liveaction=str(liveaction.id))

        self.assertEqual(len(wf_exs), 1)
        self.assertIsNotNone(wf_exs[0].id)
        self.assertGreater(wf_exs[0].rev, 0)
        self.assertIn('workflow_execution', liveaction.context)
        self.assertEqual(liveaction.context['workflow_execution'], str(wf_exs[0].id))
        self.assertIsNotNone(wf_exs[0].graph)
        self.assertTrue(isinstance(wf_exs[0].graph, dict))
        self.assertIn('nodes', wf_exs[0].graph)
        self.assertIn('adjacency', wf_exs[0].graph)
        self.assertIsNotNone(wf_exs[0].flow)
        self.assertTrue(isinstance(wf_exs[0].flow, dict))
        self.assertIn('tasks', wf_exs[0].flow)
        self.assertIn('sequence', wf_exs[0].flow)

    def test_workflow_inspection_failure(self):
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, TEST_FIXTURES['workflows'][1])
        liveaction = LiveActionDB(action=wf_meta['name'])
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))

        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_FAILED)
        self.assertIn('errors', liveaction.result)
        self.assertIn('expressions', liveaction.result['errors'])
        self.assertGreater(len(liveaction.result['errors']['expressions']), 0)
        self.assertIn('context', liveaction.result['errors'])
        self.assertGreater(len(liveaction.result['errors']['context']), 0)
        self.assertIn('syntax', liveaction.result['errors'])
        self.assertGreater(len(liveaction.result['errors']['syntax']), 0)
