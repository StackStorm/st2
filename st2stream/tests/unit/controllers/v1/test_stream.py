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

from st2common.models.api.action import ActionAPI, RunnerTypeAPI
from st2common.models.api.execution import LiveActionAPI
from st2common.models.db.liveaction import LiveActionDB
from st2common.persistence.action import Action, RunnerType
from st2stream.controllers.v1 import stream
import st2stream.listener
from st2tests.api import SUPER_SECRET_PARAMETER
from st2api.tests.base import FunctionalTest
#from base import FunctionalTest


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


class META(object):
    delivery_info = {
        'exchange': 'some',
        'routing_key': 'thing'
    }

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
