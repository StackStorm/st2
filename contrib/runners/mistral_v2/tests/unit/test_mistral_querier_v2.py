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

import copy
import datetime
import json
import requests
import uuid

import mock
from mock import call

from mistralclient.api import base as mistralclient_base
from mistralclient.api.v2 import executions
from mistralclient.api.v2 import tasks
from oslo_config import cfg

import st2tests.config as tests_config
tests_config.parse_args()

from st2common.constants import action as action_constants
from st2common.services import action as action_service
from st2common.util import loader
from st2tests import DbTestCase


MOCK_WF_TASKS_SUCCEEDED = [
    {'name': 'task1', 'state': 'SUCCESS'},
    {'name': 'task2', 'state': 'SUCCESS'}
]

MOCK_WF_TASKS_ERRORED = [
    {'name': 'task1', 'state': 'SUCCESS'},
    {'name': 'task2', 'state': 'ERROR'}
]

MOCK_WF_TASKS_RUNNING = [
    {'name': 'task1', 'state': 'SUCCESS'},
    {'name': 'task2', 'state': 'RUNNING'}
]

MOCK_WF_TASKS_WAITING = [
    {'name': 'task1', 'state': 'SUCCESS'},
    {'name': 'task2', 'state': 'WAITING'}
]

MOCK_WF_EX_DATA = {
    'id': uuid.uuid4().hex,
    'name': 'main',
    'output': '{"k1": "v1"}',
    'state': 'SUCCESS',
    'state_info': None
}

MOCK_WF_EX = executions.Execution(None, MOCK_WF_EX_DATA)

MOCK_WF_EX_TASKS_DATA = [
    {
        'id': uuid.uuid4().hex,
        'name': 'task1',
        'workflow_execution_id': MOCK_WF_EX_DATA['id'],
        'workflow_name': MOCK_WF_EX_DATA['name'],
        'created_at': str(datetime.datetime.utcnow()),
        'updated_at': str(datetime.datetime.utcnow()),
        'state': 'SUCCESS',
        'state_info': None,
        'input': '{"a": "b"}',
        'result': '{"c": "d"}',
        'published': '{"c": "d"}'
    },
    {
        'id': uuid.uuid4().hex,
        'name': 'task2',
        'workflow_execution_id': MOCK_WF_EX_DATA['id'],
        'workflow_name': MOCK_WF_EX_DATA['name'],
        'created_at': str(datetime.datetime.utcnow()),
        'updated_at': str(datetime.datetime.utcnow()),
        'state': 'SUCCESS',
        'state_info': None,
        'input': '{"e": "f", "g": "h"}',
        'result': '{"i": "j", "k": "l"}',
        'published': '{"k": "l"}'
    }
]

MOCK_WF_EX_TASKS = [
    tasks.Task(None, MOCK_WF_EX_TASKS_DATA[0]),
    tasks.Task(None, MOCK_WF_EX_TASKS_DATA[1])
]

MOCK_QRY_CONTEXT = {
    'mistral': {
        'execution_id': uuid.uuid4().hex
    }
}


class MistralQuerierTest(DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(MistralQuerierTest, cls).setUpClass()

        # Override the retry configuration here otherwise st2tests.config.parse_args
        # in DbTestCase.setUpClass will reset these overrides.
        cfg.CONF.set_override('retry_exp_msec', 100, group='mistral')
        cfg.CONF.set_override('retry_exp_max_msec', 200, group='mistral')
        cfg.CONF.set_override('retry_stop_max_msec', 200, group='mistral')

        # Register query module.
        cls.query_module = loader.register_query_module('mistral_v2')

    def setUp(self):
        super(MistralQuerierTest, self).setUp()
        self.querier = self.query_module.get_instance()

    @mock.patch.object(
        action_service, 'is_action_canceled_or_canceling',
        mock.MagicMock(return_value=False))
    def test_determine_status_wf_running_tasks_running(self):
        wf_id = uuid.uuid4().hex
        status = self.querier._determine_execution_status(wf_id, 'RUNNING', MOCK_WF_TASKS_RUNNING)
        self.assertEqual(action_constants.LIVEACTION_STATUS_RUNNING, status)

    @mock.patch.object(
        action_service, 'is_action_canceled_or_canceling',
        mock.MagicMock(return_value=False))
    def test_determine_status_wf_running_tasks_completed(self):
        wf_id = uuid.uuid4().hex
        status = self.querier._determine_execution_status(wf_id, 'RUNNING', MOCK_WF_TASKS_SUCCEEDED)
        self.assertEqual(action_constants.LIVEACTION_STATUS_RUNNING, status)

    @mock.patch.object(
        action_service, 'is_action_canceled_or_canceling',
        mock.MagicMock(return_value=False))
    def test_determine_status_wf_succeeded_tasks_completed(self):
        wf_id = uuid.uuid4().hex
        status = self.querier._determine_execution_status(wf_id, 'SUCCESS', MOCK_WF_TASKS_SUCCEEDED)
        self.assertEqual(action_constants.LIVEACTION_STATUS_SUCCEEDED, status)

    @mock.patch.object(
        action_service, 'is_action_canceled_or_canceling',
        mock.MagicMock(return_value=False))
    def test_determine_status_wf_succeeded_tasks_running(self):
        wf_id = uuid.uuid4().hex
        status = self.querier._determine_execution_status(wf_id, 'SUCCESS', MOCK_WF_TASKS_RUNNING)
        self.assertEqual(action_constants.LIVEACTION_STATUS_RUNNING, status)

    @mock.patch.object(
        action_service, 'is_action_canceled_or_canceling',
        mock.MagicMock(return_value=False))
    def test_determine_status_wf_errored_tasks_completed(self):
        wf_id = uuid.uuid4().hex
        status = self.querier._determine_execution_status(wf_id, 'ERROR', MOCK_WF_TASKS_SUCCEEDED)
        self.assertEqual(action_constants.LIVEACTION_STATUS_FAILED, status)

    @mock.patch.object(
        action_service, 'is_action_canceled_or_canceling',
        mock.MagicMock(return_value=False))
    def test_determine_status_wf_errored_tasks_running(self):
        wf_id = uuid.uuid4().hex
        status = self.querier._determine_execution_status(wf_id, 'ERROR', MOCK_WF_TASKS_RUNNING)
        self.assertEqual(action_constants.LIVEACTION_STATUS_RUNNING, status)

    @mock.patch.object(
        action_service, 'is_action_canceled_or_canceling',
        mock.MagicMock(return_value=True))
    def test_determine_status_wf_canceled_tasks_completed(self):
        wf_id = uuid.uuid4().hex
        status = self.querier._determine_execution_status(
            wf_id, 'CANCELLED', MOCK_WF_TASKS_SUCCEEDED)
        self.assertEqual(action_constants.LIVEACTION_STATUS_CANCELED, status)

    @mock.patch.object(
        action_service, 'is_action_canceled_or_canceling',
        mock.MagicMock(return_value=True))
    def test_determine_status_wf_canceled_tasks_running(self):
        wf_id = uuid.uuid4().hex
        status = self.querier._determine_execution_status(wf_id, 'CANCELLED', MOCK_WF_TASKS_RUNNING)
        self.assertEqual(action_constants.LIVEACTION_STATUS_CANCELING, status)

    @mock.patch.object(
        action_service, 'is_action_canceled_or_canceling',
        mock.MagicMock(return_value=True))
    def test_determine_status_wf_canceled_tasks_waiting(self):
        wf_id = uuid.uuid4().hex
        status = self.querier._determine_execution_status(wf_id, 'CANCELLED', MOCK_WF_TASKS_WAITING)
        self.assertEqual(action_constants.LIVEACTION_STATUS_CANCELED, status)

    @mock.patch.object(
        action_service, 'is_action_canceled_or_canceling',
        mock.MagicMock(return_value=True))
    def test_determine_status_wf_canceled_exec_running_tasks_completed(self):
        wf_id = uuid.uuid4().hex
        status = self.querier._determine_execution_status(wf_id, 'RUNNING', MOCK_WF_TASKS_SUCCEEDED)
        self.assertEqual(action_constants.LIVEACTION_STATUS_CANCELING, status)

    @mock.patch.object(
        action_service, 'is_action_canceled_or_canceling',
        mock.MagicMock(return_value=True))
    def test_determine_status_wf_canceled_exec_running_tasks_running(self):
        wf_id = uuid.uuid4().hex
        status = self.querier._determine_execution_status(wf_id, 'RUNNING', MOCK_WF_TASKS_RUNNING)
        self.assertEqual(action_constants.LIVEACTION_STATUS_CANCELING, status)

    @mock.patch.object(
        action_service, 'is_action_canceled_or_canceling',
        mock.MagicMock(return_value=True))
    def test_determine_status_wf_canceled_exec_running_tasks_waiting(self):
        wf_id = uuid.uuid4().hex
        status = self.querier._determine_execution_status(wf_id, 'RUNNING', MOCK_WF_TASKS_WAITING)
        self.assertEqual(action_constants.LIVEACTION_STATUS_CANCELING, status)

    @mock.patch.object(
        action_service, 'is_action_canceled_or_canceling',
        mock.MagicMock(return_value=False))
    def test_determine_status_wf_running_exec_paused_tasks_completed(self):
        wf_id = uuid.uuid4().hex
        status = self.querier._determine_execution_status(
            wf_id, 'PAUSED', MOCK_WF_TASKS_SUCCEEDED)
        self.assertEqual(action_constants.LIVEACTION_STATUS_RUNNING, status)

    @mock.patch.object(
        action_service, 'is_action_canceled_or_canceling',
        mock.MagicMock(return_value=False))
    def test_determine_status_wf_running_exec_cancelled_tasks_running(self):
        wf_id = uuid.uuid4().hex
        status = self.querier._determine_execution_status(wf_id, 'CANCELLED', MOCK_WF_TASKS_RUNNING)
        self.assertEqual(action_constants.LIVEACTION_STATUS_CANCELING, status)

    @mock.patch.object(
        executions.ExecutionManager, 'get',
        mock.MagicMock(return_value=MOCK_WF_EX))
    def test_get_workflow_result(self):
        result = self.querier._get_workflow_result(uuid.uuid4().hex)

        expected = {
            'k1': 'v1',
            'extra': {
                'state': MOCK_WF_EX.state,
                'state_info': MOCK_WF_EX.state_info
            }
        }

        self.assertDictEqual(expected, result)

    @mock.patch.object(
        tasks.TaskManager, 'list',
        mock.MagicMock(return_value=MOCK_WF_EX_TASKS))
    @mock.patch.object(
        tasks.TaskManager, 'get',
        mock.MagicMock(side_effect=[
            MOCK_WF_EX_TASKS[0],
            MOCK_WF_EX_TASKS[1]]))
    def test_get_workflow_tasks(self):
        tasks = self.querier._get_workflow_tasks(uuid.uuid4().hex)

        expected = copy.deepcopy(MOCK_WF_EX_TASKS_DATA)
        for task in expected:
            task['input'] = json.loads(task['input'])
            task['result'] = json.loads(task['result'])
            task['published'] = json.loads(task['published'])

        for i in range(0, len(tasks)):
            self.assertDictEqual(expected[i], tasks[i])

    @mock.patch.object(
        executions.ExecutionManager, 'get',
        mock.MagicMock(return_value=MOCK_WF_EX))
    @mock.patch.object(
        tasks.TaskManager, 'list',
        mock.MagicMock(return_value=MOCK_WF_EX_TASKS))
    @mock.patch.object(
        tasks.TaskManager, 'get',
        mock.MagicMock(side_effect=[
            MOCK_WF_EX_TASKS[0],
            MOCK_WF_EX_TASKS[1]]))
    @mock.patch.object(
        action_service, 'is_action_canceled_or_canceling',
        mock.MagicMock(return_value=False))
    def test_query(self):
        (status, result) = self.querier.query(uuid.uuid4().hex, MOCK_QRY_CONTEXT)

        expected = {
            'k1': 'v1',
            'tasks': copy.deepcopy(MOCK_WF_EX_TASKS_DATA),
            'extra': {
                'state': MOCK_WF_EX.state,
                'state_info': MOCK_WF_EX.state_info
            }
        }

        for task in expected['tasks']:
            task['input'] = json.loads(task['input'])
            task['result'] = json.loads(task['result'])
            task['published'] = json.loads(task['published'])

        self.assertEqual(action_constants.LIVEACTION_STATUS_SUCCEEDED, status)
        self.assertDictEqual(expected, result)

    @mock.patch.object(
        executions.ExecutionManager, 'get',
        mock.MagicMock(side_effect=[
            requests.exceptions.ConnectionError(),
            MOCK_WF_EX]))
    @mock.patch.object(
        tasks.TaskManager, 'list',
        mock.MagicMock(return_value=MOCK_WF_EX_TASKS))
    @mock.patch.object(
        tasks.TaskManager, 'get',
        mock.MagicMock(side_effect=[
            MOCK_WF_EX_TASKS[0],
            MOCK_WF_EX_TASKS[1]]))
    @mock.patch.object(
        action_service, 'is_action_canceled_or_canceling',
        mock.MagicMock(return_value=False))
    def test_query_get_workflow_retry(self):
        (status, result) = self.querier.query(uuid.uuid4().hex, MOCK_QRY_CONTEXT)

        expected = {
            'k1': 'v1',
            'tasks': copy.deepcopy(MOCK_WF_EX_TASKS_DATA),
            'extra': {
                'state': MOCK_WF_EX.state,
                'state_info': MOCK_WF_EX.state_info
            }
        }

        for task in expected['tasks']:
            task['input'] = json.loads(task['input'])
            task['result'] = json.loads(task['result'])
            task['published'] = json.loads(task['published'])

        self.assertEqual(action_constants.LIVEACTION_STATUS_SUCCEEDED, status)
        self.assertDictEqual(expected, result)

        calls = [call(MOCK_QRY_CONTEXT['mistral']['execution_id']) for i in range(0, 2)]
        executions.ExecutionManager.get.assert_has_calls(calls)

    @mock.patch.object(
        executions.ExecutionManager, 'get',
        mock.MagicMock(side_effect=[requests.exceptions.ConnectionError()] * 4))
    def test_query_get_workflow_retry_exhausted(self):
        self.assertRaises(
            requests.exceptions.ConnectionError,
            self.querier.query,
            uuid.uuid4().hex,
            MOCK_QRY_CONTEXT)

        calls = [call(MOCK_QRY_CONTEXT['mistral']['execution_id']) for i in range(0, 2)]
        executions.ExecutionManager.get.assert_has_calls(calls)

    @mock.patch.object(
        executions.ExecutionManager, 'get',
        mock.MagicMock(
            side_effect=mistralclient_base.APIException(
                error_code=404, error_message='Workflow not found.')))
    def test_query_get_workflow_not_found(self):
        (status, result) = self.querier.query(uuid.uuid4().hex, MOCK_QRY_CONTEXT)

        self.assertEqual(action_constants.LIVEACTION_STATUS_FAILED, status)
        self.assertEqual('Workflow not found.', result)

    @mock.patch.object(
        executions.ExecutionManager, 'get',
        mock.MagicMock(return_value=MOCK_WF_EX))
    @mock.patch.object(
        tasks.TaskManager, 'list',
        mock.MagicMock(side_effect=[
            requests.exceptions.ConnectionError(),
            MOCK_WF_EX_TASKS]))
    @mock.patch.object(
        tasks.TaskManager, 'get',
        mock.MagicMock(side_effect=[
            MOCK_WF_EX_TASKS[0],
            MOCK_WF_EX_TASKS[1]]))
    @mock.patch.object(
        action_service, 'is_action_canceled_or_canceling',
        mock.MagicMock(return_value=False))
    def test_query_list_workflow_tasks_retry(self):
        (status, result) = self.querier.query(uuid.uuid4().hex, MOCK_QRY_CONTEXT)

        expected = {
            'k1': 'v1',
            'tasks': copy.deepcopy(MOCK_WF_EX_TASKS_DATA),
            'extra': {
                'state': MOCK_WF_EX.state,
                'state_info': MOCK_WF_EX.state_info
            }
        }

        for task in expected['tasks']:
            task['input'] = json.loads(task['input'])
            task['result'] = json.loads(task['result'])
            task['published'] = json.loads(task['published'])

        self.assertEqual(action_constants.LIVEACTION_STATUS_SUCCEEDED, status)
        self.assertDictEqual(expected, result)

        mock_call = call(workflow_execution_id=MOCK_QRY_CONTEXT['mistral']['execution_id'])
        calls = [mock_call for i in range(0, 2)]
        tasks.TaskManager.list.assert_has_calls(calls)

        calls = [call(MOCK_WF_EX_TASKS[0].id), call(MOCK_WF_EX_TASKS[1].id)]
        tasks.TaskManager.get.assert_has_calls(calls)

    @mock.patch.object(
        executions.ExecutionManager, 'get',
        mock.MagicMock(return_value=MOCK_WF_EX))
    @mock.patch.object(
        tasks.TaskManager, 'list',
        mock.MagicMock(return_value=MOCK_WF_EX_TASKS))
    @mock.patch.object(
        tasks.TaskManager, 'get',
        mock.MagicMock(side_effect=[
            requests.exceptions.ConnectionError(),
            MOCK_WF_EX_TASKS[0],
            MOCK_WF_EX_TASKS[1]]))
    @mock.patch.object(
        action_service, 'is_action_canceled_or_canceling',
        mock.MagicMock(return_value=False))
    def test_query_get_workflow_tasks_retry(self):
        (status, result) = self.querier.query(uuid.uuid4().hex, MOCK_QRY_CONTEXT)

        expected = {
            'k1': 'v1',
            'tasks': copy.deepcopy(MOCK_WF_EX_TASKS_DATA),
            'extra': {
                'state': MOCK_WF_EX.state,
                'state_info': MOCK_WF_EX.state_info
            }
        }

        for task in expected['tasks']:
            task['input'] = json.loads(task['input'])
            task['result'] = json.loads(task['result'])
            task['published'] = json.loads(task['published'])

        self.assertEqual(action_constants.LIVEACTION_STATUS_SUCCEEDED, status)
        self.assertDictEqual(expected, result)

        calls = [
            call(MOCK_WF_EX_TASKS[0].id),
            call(MOCK_WF_EX_TASKS[0].id),
            call(MOCK_WF_EX_TASKS[1].id)
        ]

        tasks.TaskManager.get.assert_has_calls(calls)

    @mock.patch.object(
        executions.ExecutionManager, 'get',
        mock.MagicMock(return_value=MOCK_WF_EX))
    @mock.patch.object(
        tasks.TaskManager, 'list',
        mock.MagicMock(side_effect=[requests.exceptions.ConnectionError()] * 4))
    def test_query_list_workflow_tasks_retry_exhausted(self):
        self.assertRaises(
            requests.exceptions.ConnectionError,
            self.querier.query,
            uuid.uuid4().hex,
            MOCK_QRY_CONTEXT)

        mock_call = call(workflow_execution_id=MOCK_QRY_CONTEXT['mistral']['execution_id'])
        calls = [mock_call for i in range(0, 2)]
        tasks.TaskManager.list.assert_has_calls(calls)

    @mock.patch.object(
        executions.ExecutionManager, 'get',
        mock.MagicMock(return_value=MOCK_WF_EX))
    @mock.patch.object(
        tasks.TaskManager, 'list',
        mock.MagicMock(return_value=MOCK_WF_EX_TASKS))
    @mock.patch.object(
        tasks.TaskManager, 'get',
        mock.MagicMock(side_effect=[requests.exceptions.ConnectionError()] * 4))
    def test_query_get_workflow_tasks_retry_exhausted(self):
        self.assertRaises(
            requests.exceptions.ConnectionError,
            self.querier.query,
            uuid.uuid4().hex,
            MOCK_QRY_CONTEXT)

        calls = [
            call(MOCK_WF_EX_TASKS[0].id),
            call(MOCK_WF_EX_TASKS[0].id)
        ]

        tasks.TaskManager.get.assert_has_calls(calls)

    @mock.patch.object(
        executions.ExecutionManager, 'get',
        mock.MagicMock(return_value=MOCK_WF_EX))
    @mock.patch.object(
        tasks.TaskManager, 'list',
        mock.MagicMock(return_value=MOCK_WF_EX_TASKS))
    @mock.patch.object(
        tasks.TaskManager, 'get',
        mock.MagicMock(
            side_effect=mistralclient_base.APIException(
                error_code=404, error_message='Task not found.')))
    def test_query_get_workflow_tasks_not_found(self):
        (status, result) = self.querier.query(uuid.uuid4().hex, MOCK_QRY_CONTEXT)

        self.assertEqual(action_constants.LIVEACTION_STATUS_FAILED, status)
        self.assertEqual('Task not found.', result)

    def test_query_missing_context(self):
        self.assertRaises(Exception, self.querier.query, uuid.uuid4().hex, {})

    def test_query_missing_mistral_execution_id(self):
        self.assertRaises(Exception, self.querier.query, uuid.uuid4().hex, {'mistral': {}})
