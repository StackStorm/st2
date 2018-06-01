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

from integration.orchestra import base

from st2common.constants import action as ac_const


class ErrorHandlingTest(base.TestWorkflowExecution):

    def test_inspection_error(self):
        expected_errors = {
            'context': [
                {
                    'type': 'yaql',
                    'expression': '<% $.foobar %>',
                    'message': 'Variable "foobar" is referenced before assignment.',
                    'schema_path': 'properties.tasks.patternProperties.^\w+$.properties.input',
                    'spec_path': 'tasks.task1.input',
                }
            ],
            'expressions': [
                {
                    'type': 'yaql',
                    'expression': '<% <% succeeded() %>',
                    'message': (
                        'Parse error: unexpected \'<\' at '
                        'position 0 of expression \'<% succeeded()\''
                    ),
                    'schema_path': (
                        'properties.tasks.patternProperties.^\w+$.'
                        'properties.next.items.properties.when'
                    ),
                    'spec_path': 'tasks.task2.next[0].when'
                }
            ],
            'syntax': [
                {
                    'message': '[{\'cmd\': \'echo <% $.macro %>\'}] is not of type \'object\'',
                    'schema_path': 'properties.tasks.patternProperties.^\w+$.properties.input.type',
                    'spec_path': 'tasks.task2.input'
                }
            ]
        }

        ex = self._execute_workflow('examples.orchestra-fail-inspection')
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(ex.result, {'errors': expected_errors, 'output': None})

    def test_input_error(self):
        expected_errors = [{'message': 'Unknown function "#property#value"'}]
        ex = self._execute_workflow('examples.orchestra-fail-input-rendering')
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(ex.result, {'errors': expected_errors, 'output': None})

    def test_vars_error(self):
        expected_errors = [{'message': 'Unknown function "#property#value"'}]
        ex = self._execute_workflow('examples.orchestra-fail-vars-rendering')
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(ex.result, {'errors': expected_errors, 'output': None})

    def test_start_task_error(self):
        expected_errors = [{'message': 'Unknown function "#property#value"', 'task_id': 'task1'}]
        ex = self._execute_workflow('examples.orchestra-fail-start-task')
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(ex.result, {'errors': expected_errors, 'output': None})

    def test_task_transition_error(self):
        expected_errors = [
            {
                'message': (
                    'Unable to resolve key \'value\' in expression \''
                    '<% succeeded() and result().value %>\' from context.'
                ),
                'task_transition_id': 'task2__0',
                'task_id': 'task1'
            }
        ]

        ex = self._execute_workflow('examples.orchestra-fail-task-transition')
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(ex.result, {'errors': expected_errors, 'output': None})

    def test_task_publish_error(self):
        expected_errors = [
            {
                'message': (
                    'Unable to resolve key \'value\' in expression \''
                    '<% result().value %>\' from context.'
                ),
                'task_transition_id': 'task2__0',
                'task_id': 'task1'
            }
        ]

        ex = self._execute_workflow('examples.orchestra-fail-task-publish')
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(ex.result, {'errors': expected_errors, 'output': None})

    def test_output_error(self):
        expected_errors = [{'message': 'Unknown function "#property#value"'}]
        ex = self._execute_workflow('examples.orchestra-fail-output-rendering')
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(ex.result, {'errors': expected_errors, 'output': None})
