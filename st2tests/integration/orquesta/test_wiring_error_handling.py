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

from integration.orquesta import base

from st2common.constants import action as ac_const


class ErrorHandlingTest(base.TestWorkflowExecution):

    def test_inspection_error(self):
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

        ex = self._execute_workflow('examples.orquesta-fail-inspection')
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(ex.result, {'errors': expected_errors, 'output': None})

    def test_input_error(self):
        expected_errors = [
            {
                'message': (
                    'Unable to evaluate expression \'<% abs(8).value %>\'. '
                    'NoFunctionRegisteredException: Unknown function "#property#value"'
                ),
            }
        ]

        ex = self._execute_workflow('examples.orquesta-fail-input-rendering')
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(ex.result, {'errors': expected_errors, 'output': None})

    def test_vars_error(self):
        expected_errors = [
            {
                'message': (
                    'Unable to evaluate expression \'<% abs(8).value %>\'. '
                    'NoFunctionRegisteredException: Unknown function "#property#value"'
                )
            }
        ]

        ex = self._execute_workflow('examples.orquesta-fail-vars-rendering')
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(ex.result, {'errors': expected_errors, 'output': None})

    def test_start_task_error(self):
        expected_errors = [
            {
                'message': (
                    'Unable to evaluate expression \'<% ctx().name.value %>\'. '
                    'NoFunctionRegisteredException: Unknown function "#property#value"'
                ),
                'task_id': 'task1'
            }
        ]

        ex = self._execute_workflow('examples.orquesta-fail-start-task')
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

        ex = self._execute_workflow('examples.orquesta-fail-task-transition')
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

        ex = self._execute_workflow('examples.orquesta-fail-task-publish')
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(ex.result, {'errors': expected_errors, 'output': None})

    def test_output_error(self):
        expected_errors = [
            {
                'message': (
                    'Unable to evaluate expression \'<% abs(8).value %>\'. '
                    'NoFunctionRegisteredException: Unknown function "#property#value"'
                )
            }
        ]

        ex = self._execute_workflow('examples.orquesta-fail-output-rendering')
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(ex.result, {'errors': expected_errors, 'output': None})

    def test_task_content_errors(self):
        expected_errors = [
            {
                'type': 'content',
                'message': 'The action reference "echo" is not formatted correctly.',
                'schema_path': r'properties.tasks.patternProperties.^\w+$.properties.action',
                'spec_path': 'tasks.task1.action'
            },
            {
                'type': 'content',
                'message': 'The action "core.echoz" is not registered in the database.',
                'schema_path': r'properties.tasks.patternProperties.^\w+$.properties.action',
                'spec_path': 'tasks.task2.action'
            },
            {
                'type': 'content',
                'message': 'Action "core.echo" is missing required input "message".',
                'schema_path': r'properties.tasks.patternProperties.^\w+$.properties.input',
                'spec_path': 'tasks.task3.input'
            },
            {
                'type': 'content',
                'message': 'Action "core.echo" has unexpected input "messages".',
                'schema_path': (
                    r'properties.tasks.patternProperties.^\w+$.properties.input.'
                    r'patternProperties.^\w+$'
                ),
                'spec_path': 'tasks.task3.input.messages'
            }
        ]

        ex = self._execute_workflow('examples.orquesta-fail-inspection-task-contents')
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(ex.result, {'errors': expected_errors, 'output': None})
