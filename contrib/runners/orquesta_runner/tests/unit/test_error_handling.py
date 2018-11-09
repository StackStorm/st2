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
import six

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
from st2common.runners import base as runners
from st2common.services import action as ac_svc
from st2common.services import workflows as wf_svc
from st2common.transport import liveaction as lv_ac_xport
from st2common.transport import workflow as wf_ex_xport
from st2common.transport import publishers
from st2tests.mocks import liveaction as mock_lv_ac_xport
from st2tests.mocks import workflow as mock_wf_ex_xport
from st2common.models.db.workflow import WorkflowExecutionDB
from st2common.models.db.workflow import TaskExecutionDB


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
class OrquestaErrorHandlingTest(st2tests.DbTestCase):
    ensure_indexes = True
    ensure_indexes_models = [
        WorkflowExecutionDB,
        TaskExecutionDB
    ]

    @classmethod
    def setUpClass(cls):
        super(OrquestaErrorHandlingTest, cls).setUpClass()

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

    def sort_wf_runtime_errors(self, errors):
        return sorted(errors, key=lambda x: x.get('task_id', None))

    def test_fail_inspection(self):
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

        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, 'fail-inspection.yaml')
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))

        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertIn('errors', lv_ac_db.result)
        self.assertListEqual(lv_ac_db.result['errors'], expected_errors)

    def test_fail_input_rendering(self):
        expected_errors = [
            {
                'message': (
                    'Unable to evaluate expression \'<% abs(4).value %>\'. '
                    'NoFunctionRegisteredException: Unknown function "#property#value"'
                )
            }
        ]

        expected_result = {'output': None, 'errors': expected_errors}

        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, 'fail-input-rendering.yaml')

        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)

        # Assert action execution for task is not started and workflow failed.
        wf_ex_db = wf_db_access.WorkflowExecution.query(action_execution=str(ac_ex_db.id))[0]
        tk_ex_dbs = wf_db_access.TaskExecution.query(workflow_execution=str(wf_ex_db.id))
        self.assertEqual(len(tk_ex_dbs), 0)
        self.assertEqual(wf_ex_db.status, wf_states.FAILED)
        self.assertListEqual(self.sort_wf_runtime_errors(wf_ex_db.errors), expected_errors)

        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(lv_ac_db.result, expected_result)

        ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db.id))
        self.assertEqual(ac_ex_db.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(ac_ex_db.result, expected_result)

    def test_fail_vars_rendering(self):
        expected_errors = [
            {
                'message': (
                    'Unable to evaluate expression \'<% abs(4).value %>\'. '
                    'NoFunctionRegisteredException: Unknown function "#property#value"'
                )
            }
        ]

        expected_result = {'output': None, 'errors': expected_errors}

        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, 'fail-vars-rendering.yaml')

        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)

        # Assert action execution for task is not started and workflow failed.
        wf_ex_db = wf_db_access.WorkflowExecution.query(action_execution=str(ac_ex_db.id))[0]
        tk_ex_dbs = wf_db_access.TaskExecution.query(workflow_execution=str(wf_ex_db.id))
        self.assertEqual(len(tk_ex_dbs), 0)
        self.assertEqual(wf_ex_db.status, wf_states.FAILED)
        self.assertListEqual(self.sort_wf_runtime_errors(wf_ex_db.errors), expected_errors)

        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(lv_ac_db.result, expected_result)

        ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db.id))
        self.assertEqual(ac_ex_db.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(ac_ex_db.result, expected_result)

    def test_fail_start_task_action(self):
        expected_errors = [
            {
                'message': (
                    'Unable to evaluate expression \'<% ctx().func.value %>\'. '
                    'NoFunctionRegisteredException: Unknown function "#property#value"'
                ),
                'task_id': 'task1'
            }
        ]

        expected_result = {'output': None, 'errors': expected_errors}

        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, 'fail-start-task-action.yaml')

        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)

        # Assert action execution for task is not started and workflow failed.
        wf_ex_db = wf_db_access.WorkflowExecution.query(action_execution=str(ac_ex_db.id))[0]
        tk_ex_dbs = wf_db_access.TaskExecution.query(workflow_execution=str(wf_ex_db.id))
        self.assertEqual(len(tk_ex_dbs), 0)
        self.assertEqual(wf_ex_db.status, wf_states.FAILED)
        self.assertListEqual(self.sort_wf_runtime_errors(wf_ex_db.errors), expected_errors)

        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(lv_ac_db.result, expected_result)

        ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db.id))
        self.assertEqual(ac_ex_db.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(ac_ex_db.result, expected_result)

    def test_fail_start_task_input_expr_eval(self):
        expected_errors = [
            {
                'message': (
                    'Unable to evaluate expression \'<% ctx().msg1.value %>\'. '
                    'NoFunctionRegisteredException: Unknown function "#property#value"'
                ),
                'task_id': 'task1'
            }
        ]

        expected_result = {'output': None, 'errors': expected_errors}

        wf_file = 'fail-start-task-input-expr-eval.yaml'
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, wf_file)

        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)

        # Assert action execution for task is not started and workflow failed.
        wf_ex_db = wf_db_access.WorkflowExecution.query(action_execution=str(ac_ex_db.id))[0]
        tk_ex_dbs = wf_db_access.TaskExecution.query(workflow_execution=str(wf_ex_db.id))
        self.assertEqual(len(tk_ex_dbs), 0)
        self.assertEqual(wf_ex_db.status, wf_states.FAILED)
        self.assertListEqual(self.sort_wf_runtime_errors(wf_ex_db.errors), expected_errors)

        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(lv_ac_db.result, expected_result)

        ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db.id))
        self.assertEqual(ac_ex_db.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(ac_ex_db.result, expected_result)

    def test_fail_start_task_input_value_type(self):
        if six.PY3:
            msg = 'Value "{\'x\': \'foobar\'}" must either be a string or None. Got "dict".'
        else:
            msg = 'Value "{u\'x\': u\'foobar\'}" must either be a string or None. Got "dict".'

        expected_errors = [
            {
                'message': msg,
                'task_id': 'task1'
            }
        ]

        expected_result = {'output': None, 'errors': expected_errors}

        wf_file = 'fail-start-task-input-value-type.yaml'
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, wf_file)
        wf_input = {'var1': {'x': 'foobar'}}
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'], parameters=wf_input)
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)

        # Assert workflow and task executions failed.
        wf_ex_db = wf_db_access.WorkflowExecution.query(action_execution=str(ac_ex_db.id))[0]
        self.assertEqual(wf_ex_db.status, wf_states.FAILED)
        self.assertListEqual(self.sort_wf_runtime_errors(wf_ex_db.errors), expected_errors)

        tk_ex_db = wf_db_access.TaskExecution.query(workflow_execution=str(wf_ex_db.id))[0]
        self.assertEqual(tk_ex_db.status, wf_states.FAILED)
        self.assertDictEqual(tk_ex_db.result, {'errors': expected_errors})

        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(lv_ac_db.result, expected_result)

        ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db.id))
        self.assertEqual(ac_ex_db.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(ac_ex_db.result, expected_result)

    def test_fail_next_task_action(self):
        expected_errors = [
            {
                'message': (
                    'Unable to evaluate expression \'<% ctx().func.value %>\'. '
                    'NoFunctionRegisteredException: Unknown function "#property#value"'
                ),
                'task_id': 'task2'
            }
        ]

        expected_result = {'output': None, 'errors': expected_errors}

        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, 'fail-task-action.yaml')

        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)

        # Assert task1 is already completed.
        wf_ex_db = wf_db_access.WorkflowExecution.query(action_execution=str(ac_ex_db.id))[0]
        tk_ex_db = wf_db_access.TaskExecution.query(workflow_execution=str(wf_ex_db.id))[0]
        tk_ac_ex_db = ex_db_access.ActionExecution.query(task_execution=str(tk_ex_db.id))[0]
        tk_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk_ac_ex_db.liveaction['id'])
        self.assertEqual(tk_lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # Manually handle action execution completion for task1 which has an error in publish.
        wf_svc.handle_action_execution_completion(tk_ac_ex_db)

        # Assert task1 succeeded but workflow failed.
        tk_ex_db = wf_db_access.TaskExecution.get_by_id(tk_ex_db.id)
        self.assertEqual(tk_ex_db.status, wf_states.SUCCEEDED)
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_states.FAILED)
        self.assertListEqual(self.sort_wf_runtime_errors(wf_ex_db.errors), expected_errors)

        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(lv_ac_db.result, expected_result)

        ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db.id))
        self.assertEqual(ac_ex_db.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(ac_ex_db.result, expected_result)

    def test_fail_next_task_input_expr_eval(self):
        expected_errors = [
            {
                'message': (
                    'Unable to evaluate expression \'<% ctx().msg2.value %>\'. '
                    'NoFunctionRegisteredException: Unknown function "#property#value"'
                ),
                'task_id': 'task2'
            }
        ]

        expected_result = {'output': None, 'errors': expected_errors}

        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, 'fail-task-input-expr-eval.yaml')

        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)

        # Assert task1 is already completed.
        wf_ex_db = wf_db_access.WorkflowExecution.query(action_execution=str(ac_ex_db.id))[0]
        tk_ex_db = wf_db_access.TaskExecution.query(workflow_execution=str(wf_ex_db.id))[0]
        tk_ac_ex_db = ex_db_access.ActionExecution.query(task_execution=str(tk_ex_db.id))[0]
        tk_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk_ac_ex_db.liveaction['id'])
        self.assertEqual(tk_lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # Manually handle action execution completion for task1 which has an error in publish.
        wf_svc.handle_action_execution_completion(tk_ac_ex_db)

        # Assert task1 succeeded but workflow failed.
        tk_ex_db = wf_db_access.TaskExecution.get_by_id(tk_ex_db.id)
        self.assertEqual(tk_ex_db.status, wf_states.SUCCEEDED)
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_states.FAILED)
        self.assertListEqual(self.sort_wf_runtime_errors(wf_ex_db.errors), expected_errors)

        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(lv_ac_db.result, expected_result)

        ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db.id))
        self.assertEqual(ac_ex_db.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(ac_ex_db.result, expected_result)

    def test_fail_next_task_input_value_type(self):
        if six.PY3:
            msg = 'Value "{\'x\': \'foobar\'}" must either be a string or None. Got "dict".'
        else:
            msg = 'Value "{u\'x\': u\'foobar\'}" must either be a string or None. Got "dict".'

        expected_errors = [
            {
                'message': msg,
                'task_id': 'task2'
            }
        ]

        expected_result = {'output': None, 'errors': expected_errors}

        wf_file = 'fail-task-input-value-type.yaml'
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, wf_file)
        wf_input = {'var1': {'x': 'foobar'}}
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'], parameters=wf_input)
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)

        # Assert task1 is already completed and workflow execution is still running.
        wf_ex_db = wf_db_access.WorkflowExecution.query(action_execution=str(ac_ex_db.id))[0]
        tk1_ex_db = wf_db_access.TaskExecution.query(workflow_execution=str(wf_ex_db.id))[0]
        tk1_ac_ex_db = ex_db_access.ActionExecution.query(task_execution=str(tk1_ex_db.id))[0]
        tk1_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk1_ac_ex_db.liveaction['id'])
        self.assertEqual(tk1_lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        self.assertEqual(wf_ex_db.status, wf_states.RUNNING)

        # Manually handle action execution completion for task1 which has an error in publish.
        wf_svc.handle_action_execution_completion(tk1_ac_ex_db)

        # Assert workflow execution and task2 execution failed.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(str(wf_ex_db.id))
        self.assertEqual(wf_ex_db.status, wf_states.FAILED)
        self.assertListEqual(self.sort_wf_runtime_errors(wf_ex_db.errors), expected_errors)

        tk2_ex_db = wf_db_access.TaskExecution.query(task_id='task2')[0]
        self.assertEqual(tk2_ex_db.status, wf_states.FAILED)
        self.assertDictEqual(tk2_ex_db.result, {'errors': expected_errors})

        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(lv_ac_db.result, expected_result)

        ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db.id))
        self.assertEqual(ac_ex_db.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(ac_ex_db.result, expected_result)

    def test_fail_task_execution(self):
        expected_errors = [
            {
                'message': 'Execution failed. See result for details.',
                'task_id': 'task1',
                'result': {
                    'stdout': '',
                    'stderr': 'boom!',
                    'return_code': 1,
                    'failed': True,
                    'succeeded': False
                }
            }
        ]

        expected_result = {'output': None, 'errors': expected_errors}

        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, 'fail-task-execution.yaml')
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)

        # Process task1.
        wf_ex_db = wf_db_access.WorkflowExecution.query(action_execution=str(ac_ex_db.id))[0]
        tk1_ex_db = wf_db_access.TaskExecution.query(workflow_execution=str(wf_ex_db.id))[0]
        tk1_ac_ex_db = ex_db_access.ActionExecution.query(task_execution=str(tk1_ex_db.id))[0]
        tk1_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk1_ac_ex_db.liveaction['id'])
        self.assertEqual(tk1_lv_ac_db.status, ac_const.LIVEACTION_STATUS_FAILED)
        wf_svc.handle_action_execution_completion(tk1_ac_ex_db)

        # Assert workflow state and result.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(str(wf_ex_db.id))
        self.assertEqual(wf_ex_db.status, wf_states.FAILED)
        self.assertListEqual(self.sort_wf_runtime_errors(wf_ex_db.errors), expected_errors)

        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(lv_ac_db.result, expected_result)

        ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db.id))
        self.assertEqual(ac_ex_db.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(ac_ex_db.result, expected_result)

    def test_fail_task_transition(self):
        expected_errors = [
            {
                'message': (
                    "Unable to resolve key 'foobar' in expression "
                    "'<% succeeded() and result().foobar %>' from context."
                ),
                'task_transition_id': 'task2__0',
                'task_id': 'task1'
            }
        ]

        expected_result = {'output': None, 'errors': expected_errors}

        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, 'fail-task-transition.yaml')
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)

        # Assert task1 is already completed.
        wf_ex_db = wf_db_access.WorkflowExecution.query(action_execution=str(ac_ex_db.id))[0]
        tk_ex_db = wf_db_access.TaskExecution.query(workflow_execution=str(wf_ex_db.id))[0]
        tk_ac_ex_db = ex_db_access.ActionExecution.query(task_execution=str(tk_ex_db.id))[0]
        tk_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk_ac_ex_db.liveaction['id'])
        self.assertEqual(tk_lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # Manually handle action execution completion for task1 which has an error in publish.
        wf_svc.handle_action_execution_completion(tk_ac_ex_db)

        # Assert task1 succeeded but workflow failed.
        tk_ex_db = wf_db_access.TaskExecution.get_by_id(tk_ex_db.id)
        self.assertEqual(tk_ex_db.status, wf_states.SUCCEEDED)
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_states.FAILED)
        self.assertListEqual(self.sort_wf_runtime_errors(wf_ex_db.errors), expected_errors)

        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(lv_ac_db.result, expected_result)

        ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db.id))
        self.assertEqual(ac_ex_db.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(ac_ex_db.result, expected_result)

    def test_fail_task_publish(self):
        expected_errors = [
            {
                'message': (
                    'Unable to evaluate expression \'<% foobar() %>\'. '
                    'NoFunctionRegisteredException: Unknown function "foobar"'
                ),
                'task_transition_id': 'task2__0',
                'task_id': 'task1'
            }
        ]

        expected_result = {'output': None, 'errors': expected_errors}

        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, 'fail-task-publish.yaml')
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)

        # Assert task1 is already completed.
        wf_ex_db = wf_db_access.WorkflowExecution.query(action_execution=str(ac_ex_db.id))[0]
        tk_ex_db = wf_db_access.TaskExecution.query(workflow_execution=str(wf_ex_db.id))[0]
        tk_ac_ex_db = ex_db_access.ActionExecution.query(task_execution=str(tk_ex_db.id))[0]
        tk_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk_ac_ex_db.liveaction['id'])
        self.assertEqual(tk_lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # Manually handle action execution completion for task1 which has an error in publish.
        wf_svc.handle_action_execution_completion(tk_ac_ex_db)

        # Assert task1 succeeded but workflow failed.
        tk_ex_db = wf_db_access.TaskExecution.get_by_id(tk_ex_db.id)
        self.assertEqual(tk_ex_db.status, wf_states.SUCCEEDED)
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_states.FAILED)
        self.assertListEqual(self.sort_wf_runtime_errors(wf_ex_db.errors), expected_errors)

        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(lv_ac_db.result, expected_result)

        ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db.id))
        self.assertEqual(ac_ex_db.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(ac_ex_db.result, expected_result)

    def test_fail_output_rendering(self):
        expected_errors = [
            {
                'message': (
                    'Unable to evaluate expression \'<% abs(4).value %>\'. '
                    'NoFunctionRegisteredException: Unknown function "#property#value"'
                )
            }
        ]

        expected_result = {'output': None, 'errors': expected_errors}

        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, 'fail-output-rendering.yaml')
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)

        # Assert task1 is already completed.
        wf_ex_db = wf_db_access.WorkflowExecution.query(action_execution=str(ac_ex_db.id))[0]
        tk_ex_db = wf_db_access.TaskExecution.query(workflow_execution=str(wf_ex_db.id))[0]
        tk_ac_ex_db = ex_db_access.ActionExecution.query(task_execution=str(tk_ex_db.id))[0]
        tk_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk_ac_ex_db.liveaction['id'])
        self.assertEqual(tk_lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # Manually handle action execution completion for task1 which has an error in publish.
        wf_svc.handle_action_execution_completion(tk_ac_ex_db)

        # Assert task1 succeeded but workflow failed.
        tk_ex_db = wf_db_access.TaskExecution.get_by_id(tk_ex_db.id)
        self.assertEqual(tk_ex_db.status, wf_states.SUCCEEDED)
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_states.FAILED)
        self.assertListEqual(self.sort_wf_runtime_errors(wf_ex_db.errors), expected_errors)

        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(lv_ac_db.result, expected_result)

        ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db.id))
        self.assertEqual(ac_ex_db.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(ac_ex_db.result, expected_result)
