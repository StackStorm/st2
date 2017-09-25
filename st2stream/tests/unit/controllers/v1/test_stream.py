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

from oslo_config import cfg

from st2common.models.api.action import ActionAPI
from st2common.models.api.action import RunnerTypeAPI
from st2common.models.api.execution import ActionExecutionAPI
from st2common.models.api.execution import LiveActionAPI
from st2common.models.db.liveaction import LiveActionDB
from st2common.models.db.execution import ActionExecutionDB
from st2common.persistence.action import Action, RunnerType
import st2stream.listener
from st2stream.controllers.v1 import stream
from st2tests.api import SUPER_SECRET_PARAMETER
from base import FunctionalTest


RUNNER_TYPE_1 = {
    'description': '',
    'enabled': True,
    'name': 'local-shell-cmd',
    'runner_module': 'local_runner',
    'runner_parameters': {}
}

ACTION_1 = {
    'name': 'st2.dummy.action1',
    'description': 'test description',
    'enabled': True,
    'entry_point': '/tmp/test/action1.sh',
    'pack': 'sixpack',
    'runner_type': 'local-shell-cmd',
    'parameters': {
        'a': {
            'type': 'string',
            'default': 'abc'
        },
        'b': {
            'type': 'number',
            'default': 123
        },
        'c': {
            'type': 'number',
            'default': 123,
            'immutable': True
        },
        'd': {
            'type': 'string',
            'secret': True
        }
    }
}

LIVE_ACTION_1 = {
    'action': 'sixpack.st2.dummy.action1',
    'parameters': {
        'hosts': 'localhost',
        'cmd': 'uname -a',
        'd': SUPER_SECRET_PARAMETER
    }
}

EXECUTION_1 = {
    'id': '598dbf0c0640fd54bffc688b',
    'action': {
        'ref': 'sixpack.st2.dummy.action1'
    },
    'parameters': {
        'hosts': 'localhost',
        'cmd': 'uname -a',
        'd': SUPER_SECRET_PARAMETER
    }
}


class META(object):
    delivery_info = {}

    def __init__(self, exchange='some', routing_key='thing'):
        self.delivery_info['exchange'] = exchange
        self.delivery_info['routing_key'] = routing_key

    def ack(self):
        pass


class TestStreamController(FunctionalTest):

    @classmethod
    def setUpClass(cls):
        super(TestStreamController, cls).setUpClass()

        instance = RunnerTypeAPI(**RUNNER_TYPE_1)
        RunnerType.add_or_update(RunnerTypeAPI.to_model(instance))

        instance = ActionAPI(**ACTION_1)
        Action.add_or_update(ActionAPI.to_model(instance))

    @mock.patch.object(st2stream.listener, 'listen', mock.Mock())
    def test_get_all(self):
        resp = stream.StreamController().get_all()
        self.assertEqual(resp._status, '200 OK')
        self.assertIn(('Content-Type', 'text/event-stream; charset=UTF-8'), resp._headerlist)

        listener = st2stream.listener.get_listener()
        process = listener.processor(LiveActionAPI)

        message = None

        for message in resp._app_iter:
            if message != '\n':
                break
            process(LiveActionDB(**LIVE_ACTION_1), META())

        self.assertIn('event: some__thing', message)
        self.assertIn('data: {"', message)
        self.assertNotIn(SUPER_SECRET_PARAMETER, message)

    @mock.patch.object(st2stream.listener, 'listen', mock.Mock())
    def test_get_all_with_filters(self):
        cfg.CONF.set_override(name='heartbeat', group='stream', override=0.1)

        listener = st2stream.listener.get_listener()
        process_execution = listener.processor(ActionExecutionAPI)
        process_liveaction = listener.processor(LiveActionAPI)

        execution_api = ActionExecutionDB(**EXECUTION_1)
        liveaction_api = LiveActionDB(**LIVE_ACTION_1)
        liveaction_api_2 = LiveActionDB(**LIVE_ACTION_1)
        liveaction_api_2.action = 'dummy.action1'

        def dispatch_and_handle_mock_data(resp):
            received_messages_data = ''
            for index, message in enumerate(resp._app_iter):
                if message.strip():
                    received_messages_data += message

                # Dispatch some mock events
                if index == 0:
                    meta = META('st2.execution', 'create')
                    process_execution(execution_api, meta)
                elif index == 1:
                    meta = META('st2.execution', 'update')
                    process_execution(execution_api, meta)
                elif index == 2:
                    meta = META('st2.execution', 'delete')
                    process_execution(execution_api, meta)
                elif index == 3:
                    meta = META('st2.liveaction', 'create')
                    process_liveaction(liveaction_api, meta)
                elif index == 4:
                    meta = META('st2.liveaction', 'create')
                    process_liveaction(liveaction_api, meta)
                elif index == 5:
                    meta = META('st2.liveaction', 'delete')
                    process_liveaction(liveaction_api_2, meta)
                else:
                    break

            received_messages = received_messages_data.split('\n\n')
            received_messages = [message for message in received_messages if message]
            return received_messages

        # 1. Default filter
        resp = stream.StreamController().get_all()

        received_messages = dispatch_and_handle_mock_data(resp)
        self.assertEqual(len(received_messages), 6)

        # 1. ?events= filter
        # No filter provided - all messages should be received
        resp = stream.StreamController().get_all()

        received_messages = dispatch_and_handle_mock_data(resp)
        self.assertEqual(len(received_messages), 6)

        # Filter provided, only two messages should be received
        events = ['st2.execution__create', 'st2.liveaction__delete']
        events = ','.join(events)
        resp = stream.StreamController().get_all(events=events)

        received_messages = dispatch_and_handle_mock_data(resp)
        self.assertEqual(len(received_messages), 2)

        # Filter provided, invalid , no message should be received
        events = ['invalid1', 'invalid2']
        events = ','.join(events)
        resp = stream.StreamController().get_all(events=events)

        received_messages = dispatch_and_handle_mock_data(resp)
        self.assertEqual(len(received_messages), 0)

        # 2. ?action_refs= filter
        action_refs = ['invalid1', 'invalid2']
        action_refs = ','.join(action_refs)
        resp = stream.StreamController().get_all(action_refs=action_refs)

        received_messages = dispatch_and_handle_mock_data(resp)
        self.assertEqual(len(received_messages), 0)

        action_refs = ['dummy.action1']
        action_refs = ','.join(action_refs)
        resp = stream.StreamController().get_all(action_refs=action_refs)

        received_messages = dispatch_and_handle_mock_data(resp)
        self.assertEqual(len(received_messages), 1)

        # 3. ?execution_ids= filter
        execution_ids = ['invalid1', 'invalid2']
        execution_ids = ','.join(execution_ids)
        resp = stream.StreamController().get_all(execution_ids=execution_ids)

        received_messages = dispatch_and_handle_mock_data(resp)
        self.assertEqual(len(received_messages), 0)

        execution_ids = [EXECUTION_1['id']]
        execution_ids = ','.join(execution_ids)
        resp = stream.StreamController().get_all(execution_ids=execution_ids)

        received_messages = dispatch_and_handle_mock_data(resp)
        self.assertEqual(len(received_messages), 3)
