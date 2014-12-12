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

from st2api import listener
from st2tests import DbTestCase


class ListenerTest(DbTestCase):

    @mock.patch.object(listener.Listener, 'emit')
    def test_processor(self, emit):
        model = type('Model', (object,), {
            'from_model': mock.Mock(return_value='model')
        })
        ack = mock.Mock()

        process = listener.Listener(mock.Mock()).processor(model)

        self.assertTrue(hasattr(process, '__call__'))

        process('body', type('message', (object,), {
            'delivery_info': {
                'exchange': 'exchange',
                'routing_key': 'routing_key'
            },
            'ack': ack
        }))

        emit.assert_called_once_with('exchange__routing_key', 'model')
        ack.assert_called_once_with()

    def test_emit(self):
        listen = listener.Listener(mock.Mock())
        put1 = mock.Mock()
        put2 = mock.Mock()
        queue1 = type('queue', (object,), {
            'put': put1
        })
        queue2 = type('queue', (object,), {
            'put': put2
        })

        listen.queues = [queue1, queue2]

        listen.emit('event', 'body')

        put1.assert_called_once_with(('event', 'body'))
        put2.assert_called_once_with(('event', 'body'))
