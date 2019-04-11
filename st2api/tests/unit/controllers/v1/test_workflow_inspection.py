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

from six.moves import http_client

from st2common.bootstrap import actionsregistrar
from st2common.bootstrap import runnersregistrar

import st2tests
from st2tests.api import FunctionalTest


TEST_PACK = 'orquesta_tests'
TEST_PACK_PATH = st2tests.fixturesloader.get_fixtures_packs_base_path() + '/' + TEST_PACK
PACKS = [TEST_PACK_PATH, st2tests.fixturesloader.get_fixtures_packs_base_path() + '/core']


class WorkflowInspectionControllerTest(FunctionalTest, st2tests.WorkflowTestCase):

    @classmethod
    def setUpClass(cls):
        super(WorkflowInspectionControllerTest, cls).setUpClass()
        st2tests.WorkflowTestCase.setUpClass()

        # Register runners.
        runnersregistrar.register_runners()

        # Register test pack(s).
        actions_registrar = actionsregistrar.ActionsRegistrar(
            use_pack_cache=False,
            fail_on_failure=True
        )

        for pack in PACKS:
            actions_registrar.register_from_pack(pack)

    def _do_post(self, wf_def, expect_errors=False):
        return self.app.post(
            '/v1/workflows/inspect',
            wf_def,
            expect_errors=expect_errors,
            content_type='text/plain'
        )

    def test_inspection(self):
        wf_file = 'sequential.yaml'
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, wf_file)
        wf_def = self.get_wf_def(TEST_PACK_PATH, wf_meta)

        expected_errors = []
        response = self._do_post(wf_def, expect_errors=False)
        self.assertEqual(http_client.OK, response.status_int)
        self.assertListEqual(response.json, expected_errors)

    def test_inspection_return_errors(self):
        wf_file = 'fail-inspection.yaml'
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, wf_file)
        wf_def = self.get_wf_def(TEST_PACK_PATH, wf_meta)

        expected_errors = [
            {
                'type': 'content',
                'message': 'The action "std.noop" is not registered in the database.',
                'schema_path': r'properties.tasks.patternProperties.^\w+$.properties.action',
                'spec_path': 'tasks.task3.action'
            },
            {
                'type': 'context',
                'language': 'yaql',
                'expression': '<% ctx().foobar %>',
                'message': 'Variable "foobar" is referenced before assignment.',
                'schema_path': r'properties.tasks.patternProperties.^\w+$.properties.input',
                'spec_path': 'tasks.task1.input',
            },
            {
                'type': 'expression',
                'language': 'yaql',
                'expression': '<% <% succeeded() %>',
                'message': (
                    'Parse error: unexpected \'<\' at '
                    'position 0 of expression \'<% succeeded()\''
                ),
                'schema_path': (
                    r'properties.tasks.patternProperties.^\w+$.'
                    'properties.next.items.properties.when'
                ),
                'spec_path': 'tasks.task2.next[0].when'
            },
            {
                'type': 'syntax',
                'message': (
                    '[{\'cmd\': \'echo <% ctx().macro %>\'}] is '
                    'not valid under any of the given schemas'
                ),
                'schema_path': r'properties.tasks.patternProperties.^\w+$.properties.input.oneOf',
                'spec_path': 'tasks.task2.input'
            }
        ]

        response = self._do_post(wf_def, expect_errors=False)
        self.assertEqual(http_client.OK, response.status_int)
        self.assertListEqual(response.json, expected_errors)
