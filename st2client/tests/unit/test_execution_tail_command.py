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

import mock
import json

from tests import base
from tests.base import BaseCLITestCase

from st2client.utils import httpclient
from st2client.commands.action import LIVEACTION_STATUS_SUCCEEDED
from st2client.commands.action import LIVEACTION_STATUS_FAILED
from st2client.commands.action import LIVEACTION_STATUS_RUNNING
from st2client.shell import Shell

__all__ = [
    'ActionExecutionTailCommandTestCase'
]

# Mock objects
MOCK_LIVEACTION_1 = {
    'id': 'idfoo1',
    'status': LIVEACTION_STATUS_SUCCEEDED
}

MOCK_LIVEACTION_2 = {
    'id': 'idfoo2',
    'status': LIVEACTION_STATUS_FAILED
}

MOCK_LIVEACTION_3_RUNNING = {
    'id': 'idfoo3',
    'status': LIVEACTION_STATUS_RUNNING
}

# Mock liveaction objects for ActionChain workflow
MOCK_LIVEACTION_3_CHILD_1_RUNNING = {
    'id': 'idchild1',
    'context': {
        'parent': {
            'execution_id': 'idfoo3'
        },
        'chain': {
            'name': 'task_1'
        }
    },
    'status': LIVEACTION_STATUS_RUNNING
}

MOCK_LIVEACTION_3_CHILD_1_SUCCEEDED = {
    'id': 'idchild1',
    'context': {
        'parent': {
            'execution_id': 'idfoo3'
        },
        'chain': {
            'name': 'task_1'
        }
    },
    'status': LIVEACTION_STATUS_SUCCEEDED
}

MOCK_LIVEACTION_3_CHILD_1_OUTPUT_1 = {
    'execution_id': 'idchild1',
    'timestamp': '1505732598',
    'output_type': 'stdout',
    'data': 'line 4\n'
}

MOCK_LIVEACTION_3_CHILD_1_OUTPUT_2 = {
    'execution_id': 'idchild1',
    'timestamp': '1505732598',
    'output_type': 'stderr',
    'data': 'line 5\n'
}

MOCK_LIVEACTION_3_CHILD_2_RUNNING = {
    'id': 'idchild2',
    'context': {
        'parent': {
            'execution_id': 'idfoo3'
        },
        'chain': {
            'name': 'task_2'
        }
    },
    'status': LIVEACTION_STATUS_RUNNING
}

MOCK_LIVEACTION_3_CHILD_2_FAILED = {
    'id': 'idchild2',
    'context': {
        'parent': {
            'execution_id': 'idfoo3'
        },
        'chain': {
            'name': 'task_2'
        }
    },
    'status': LIVEACTION_STATUS_FAILED
}

MOCK_LIVEACTION_3_CHILD_2_OUTPUT_1 = {
    'execution_id': 'idchild2',
    'timestamp': '1505732598',
    'output_type': 'stdout',
    'data': 'line 100\n'
}

MOCK_LIVEACTION_3_SUCCEDED = {
    'id': 'idfoo3',
    'status': LIVEACTION_STATUS_SUCCEEDED
}

# Mock objects for simple actions

MOCK_OUTPUT_1 = {
    'execution_id': 'idfoo3',
    'timestamp': '1505732598',
    'output_type': 'stdout',
    'data': 'line 1\n'
}

MOCK_OUTPUT_2 = {
    'execution_id': 'idfoo3',
    'timestamp': '1505732598',
    'output_type': 'stderr',
    'data': 'line 2\n'
}


class ActionExecutionTailCommandTestCase(BaseCLITestCase):
    capture_output = True
    #capture_output = False

    def __init__(self, *args, **kwargs):
        super(ActionExecutionTailCommandTestCase, self).__init__(*args, **kwargs)
        self.shell = Shell()

    @mock.patch.object(
        httpclient.HTTPClient, 'get',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(MOCK_LIVEACTION_1), 200, 'OK')))
    def test_tail_simple_execution_already_finished_succeeded(self):
        argv = ['execution', 'tail', 'idfoo1']

        self.assertEqual(self.shell.run(argv), 0)
        stdout = self.stdout.getvalue()
        stderr = self.stderr.getvalue()
        self.assertTrue('Execution idfoo1 has completed (status=succeeded)' in stdout)
        self.assertEqual(stderr, '')

    @mock.patch.object(
        httpclient.HTTPClient, 'get',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(MOCK_LIVEACTION_2), 200, 'OK')))
    def test_tail_simple_execution_already_finished_failed(self):
        argv = ['execution', 'tail', 'idfoo2']

        self.assertEqual(self.shell.run(argv), 0)
        stdout = self.stdout.getvalue()
        stderr = self.stderr.getvalue()
        self.assertTrue('Execution idfoo2 has completed (status=failed)' in stdout)
        self.assertEqual(stderr, '')

    @mock.patch.object(
        httpclient.HTTPClient, 'get',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(MOCK_LIVEACTION_3_RUNNING), 200, 'OK')))
    @mock.patch('st2client.client.StreamManager', autospec=True)
    def test_tail_simple_execution_running_no_data_produced(self, mock_stream_manager):
        argv = ['execution', 'tail', 'idfoo1']

        MOCK_EVENTS = [
            MOCK_LIVEACTION_1
        ]

        mock_cls = mock.Mock()
        mock_cls.listen = mock.Mock()
        mock_listen_generator = mock.Mock()
        mock_listen_generator.return_value = MOCK_EVENTS
        mock_cls.listen.side_effect = mock_listen_generator
        mock_stream_manager.return_value = mock_cls

        self.assertEqual(self.shell.run(argv), 0)
        self.assertEqual(mock_listen_generator.call_count, 1)

        stdout = self.stdout.getvalue()
        stderr = self.stderr.getvalue()

        expected_result = """
Execution idfoo1 has completed (status=succeeded).
"""
        self.assertEqual(stdout, expected_result)
        self.assertEqual(stderr, '')

    @mock.patch.object(
        httpclient.HTTPClient, 'get',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(MOCK_LIVEACTION_3_RUNNING), 200, 'OK')))
    @mock.patch('st2client.client.StreamManager', autospec=True)
    def test_tail_simple_execution_running_with_data(self, mock_stream_manager):
        argv = ['execution', 'tail', 'idfoo1']

        MOCK_EVENTS = [
            MOCK_LIVEACTION_3_RUNNING,
            MOCK_OUTPUT_1,
            MOCK_OUTPUT_2,
            MOCK_LIVEACTION_1
        ]

        mock_cls = mock.Mock()
        mock_cls.listen = mock.Mock()
        mock_listen_generator = mock.Mock()
        mock_listen_generator.return_value = MOCK_EVENTS
        mock_cls.listen.side_effect = mock_listen_generator
        mock_stream_manager.return_value = mock_cls

        self.assertEqual(self.shell.run(argv), 0)
        self.assertEqual(mock_listen_generator.call_count, 1)

        stdout = self.stdout.getvalue()
        stderr = self.stderr.getvalue()

        expected_result = """
line 1
line 2

Execution idfoo1 has completed (status=succeeded).
""".lstrip()
        self.assertEqual(stdout, expected_result)
        self.assertEqual(stderr, '')

    @mock.patch.object(
        httpclient.HTTPClient, 'get',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(MOCK_LIVEACTION_3_RUNNING), 200, 'OK')))
    @mock.patch('st2client.client.StreamManager', autospec=True)
    def test_tail_action_chain_workflow_execution(self, mock_stream_manager):
        argv = ['execution', 'tail', 'idfoo3']

        MOCK_EVENTS = [
            # Workflow started running
            MOCK_LIVEACTION_3_RUNNING,

            # Child task 1 started running
            MOCK_LIVEACTION_3_CHILD_1_RUNNING,

            # Output produced by the child task
            MOCK_LIVEACTION_3_CHILD_1_OUTPUT_1,
            MOCK_LIVEACTION_3_CHILD_1_OUTPUT_2,

            # Child task 1 finished
            MOCK_LIVEACTION_3_CHILD_1_SUCCEEDED,

            # Child task 2 started running
            MOCK_LIVEACTION_3_CHILD_2_RUNNING,

            # Output produced by child task
            MOCK_LIVEACTION_3_CHILD_2_OUTPUT_1,

            # Child task 2 finished
            MOCK_LIVEACTION_3_CHILD_2_FAILED,

            # Parent workflow task finished
            MOCK_LIVEACTION_3_SUCCEDED
        ]

        mock_cls = mock.Mock()
        mock_cls.listen = mock.Mock()
        mock_listen_generator = mock.Mock()
        mock_listen_generator.return_value = MOCK_EVENTS
        mock_cls.listen.side_effect = mock_listen_generator
        mock_stream_manager.return_value = mock_cls

        self.assertEqual(self.shell.run(argv), 0)
        self.assertEqual(mock_listen_generator.call_count, 1)

        stdout = self.stdout.getvalue()
        stderr = self.stderr.getvalue()

        expected_result = """
Child execution (task=task_1) idchild1 has started.

line 4
line 5

Child execution (task=task_1) idchild1 has finished (status=succeeded).
Child execution (task=task_2) idchild2 has started.

line 100

Child execution (task=task_2) idchild2 has finished (status=failed).

Execution idfoo3 has completed (status=succeeded).
""".lstrip()
        self.assertEqual(stdout, expected_result)
        self.assertEqual(stderr, '')

    def test_tail_mistral_workflow_execution(self):
        return
