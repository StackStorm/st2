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

import eventlet
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
                'type': 'error',
                'message': (
                    'YaqlEvaluationException: Unable to evaluate expression '
                    '\'<% abs(8).value %>\'. NoFunctionRegisteredException: '
                    'Unknown function "#property#value"'
                )
            }
        ]

        ex = self._execute_workflow('examples.orquesta-fail-input-rendering')
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(ex.result, {'errors': expected_errors, 'output': None})

    def test_vars_error(self):
        expected_errors = [
            {
                'type': 'error',
                'message': (
                    'YaqlEvaluationException: Unable to evaluate expression '
                    '\'<% abs(8).value %>\'. NoFunctionRegisteredException: '
                    'Unknown function "#property#value"'
                )
            }
        ]

        ex = self._execute_workflow('examples.orquesta-fail-vars-rendering')
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(ex.result, {'errors': expected_errors, 'output': None})

    def test_start_task_error(self):
        self.maxDiff = None

        expected_errors = [
            {
                'type': 'error',
                'message': (
                    'YaqlEvaluationException: Unable to evaluate expression '
                    '\'<% ctx().name.value %>\'. NoFunctionRegisteredException: '
                    'Unknown function "#property#value"'
                ),
                'task_id': 'task1',
                'route': 0
            },
            {
                'type': 'error',
                'message': (
                    'YaqlEvaluationException: Unable to resolve key \'greeting\' '
                    'in expression \'<% ctx().greeting %>\' from context.'
                )
            }
        ]

        ex = self._execute_workflow('examples.orquesta-fail-start-task')
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(ex.result, {'errors': expected_errors, 'output': None})

    def test_task_transition_error(self):
        expected_errors = [
            {
                'type': 'error',
                'message': (
                    'YaqlEvaluationException: Unable to resolve key \'value\' '
                    'in expression \'<% succeeded() and result().value %>\' from context.'
                ),
                'task_transition_id': 'task2__t0',
                'task_id': 'task1',
                'route': 0
            }
        ]

        expected_output = {
            'greeting': None
        }

        ex = self._execute_workflow('examples.orquesta-fail-task-transition')
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(ex.result, {'errors': expected_errors, 'output': expected_output})

    def test_task_publish_error(self):
        expected_errors = [
            {
                'type': 'error',
                'message': (
                    'YaqlEvaluationException: Unable to resolve key \'value\' '
                    'in expression \'<% result().value %>\' from context.'
                ),
                'task_transition_id': 'task2__t0',
                'task_id': 'task1',
                'route': 0
            }
        ]

        expected_output = {
            'greeting': None
        }

        ex = self._execute_workflow('examples.orquesta-fail-task-publish')
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(ex.result, {'errors': expected_errors, 'output': expected_output})

    def test_output_error(self):
        expected_errors = [
            {
                'type': 'error',
                'message': (
                    'YaqlEvaluationException: Unable to evaluate expression '
                    '\'<% abs(8).value %>\'. NoFunctionRegisteredException: '
                    'Unknown function "#property#value"'
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

    def test_remediate_then_fail(self):
        expected_errors = [
            {
                'task_id': 'task1',
                'type': 'error',
                'message': 'Execution failed. See result for details.',
                'result': {
                    'failed': True,
                    'return_code': 1,
                    'stderr': '',
                    'stdout': '',
                    'succeeded': False
                }
            },
            {
                'task_id': 'fail',
                'type': 'error',
                'message': 'Execution failed. See result for details.'
            }
        ]

        ex = self._execute_workflow('examples.orquesta-remediate-then-fail')
        ex = self._wait_for_completion(ex)

        # Assert that the log task is executed.
        # NOTE: There is a race wheen execution gets in a desired state, but before the child
        # tasks are written. To avoid that, we use longer sleep delay here.
        # Better approach would be to try to retry a couple of times until expected num of
        # tasks is reached (With some hard limit) before failing
        eventlet.sleep(2)

        self._wait_for_task(ex, 'task1', ac_const.LIVEACTION_STATUS_FAILED)
        self._wait_for_task(ex, 'log', ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # Assert workflow status and result.
        self.assertEqual(ex.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(ex.result, {'errors': expected_errors, 'output': None})

    def test_fail_manually(self):
        expected_errors = [
            {
                'task_id': 'task1',
                'type': 'error',
                'message': 'Execution failed. See result for details.',
                'result': {
                    'failed': True,
                    'return_code': 1,
                    'stderr': '',
                    'stdout': '',
                    'succeeded': False
                }
            },
            {
                'task_id': 'fail',
                'type': 'error',
                'message': 'Execution failed. See result for details.'
            }
        ]

        expected_output = {
            'message': '$%#&@#$!!!'
        }

        wf_input = {'cmd': 'exit 1'}
        ex = self._execute_workflow('examples.orquesta-error-handling-fail-manually', wf_input)
        ex = self._wait_for_completion(ex)

        # Assert task status.
        self._wait_for_task(ex, 'task1', ac_const.LIVEACTION_STATUS_FAILED)
        self._wait_for_task(ex, 'task3', ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # Assert workflow status and result.
        self.assertEqual(ex.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(ex.result, {'errors': expected_errors, 'output': expected_output})

    def test_fail_continue(self):
        expected_errors = [
            {
                'task_id': 'task1',
                'type': 'error',
                'message': 'Execution failed. See result for details.',
                'result': {
                    'failed': True,
                    'return_code': 1,
                    'stderr': '',
                    'stdout': '',
                    'succeeded': False
                }
            }
        ]

        expected_output = {
            'message': '$%#&@#$!!!'
        }

        wf_input = {'cmd': 'exit 1'}
        ex = self._execute_workflow('examples.orquesta-error-handling-continue', wf_input)
        ex = self._wait_for_completion(ex)

        # Assert task status.
        self._wait_for_task(ex, 'task1', ac_const.LIVEACTION_STATUS_FAILED)

        # Assert workflow status and result.
        self.assertEqual(ex.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(ex.result, {'errors': expected_errors, 'output': expected_output})

    def test_fail_noop(self):
        expected_output = {
            'message': '$%#&@#$!!!'
        }

        wf_input = {'cmd': 'exit 1'}
        ex = self._execute_workflow('examples.orquesta-error-handling-noop', wf_input)
        ex = self._wait_for_completion(ex)

        # Assert task status.
        self._wait_for_task(ex, 'task1', ac_const.LIVEACTION_STATUS_FAILED)

        # Assert workflow status and result.
        self.assertEqual(ex.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        self.assertDictEqual(ex.result, {'output': expected_output})
