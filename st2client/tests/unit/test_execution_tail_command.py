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

MOCK_LIVEACTION_3 = {
    'id': 'idfoo3',
    'status': LIVEACTION_STATUS_RUNNING
}

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
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(MOCK_LIVEACTION_3), 200, 'OK')))
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
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(MOCK_LIVEACTION_3), 200, 'OK')))
    @mock.patch('st2client.client.StreamManager', autospec=True)
    def test_tail_simple_execution_running_with_data(self, mock_stream_manager):
        argv = ['execution', 'tail', 'idfoo1']

        MOCK_EVENTS = [
            MOCK_LIVEACTION_3,
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

    def test_tail_action_chain_workflow_execution(self):
        return

    def test_tail_mistral_workflow_execution(self):
        return
