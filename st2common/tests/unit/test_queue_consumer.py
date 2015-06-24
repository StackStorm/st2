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
from kombu import Connection, Exchange, Queue
from oslo_config import cfg

from st2common.transport import consumers
from st2tests.base import DbTestCase
from tests.unit.base import FakeModelDB


FAKE_XCHG = Exchange('st2.tests', type='topic')
FAKE_WORK_Q = Queue('st2.tests.unit', FAKE_XCHG)


class FakeMessageHandler(consumers.MessageHandler):
    message_type = FakeModelDB

    def process(self, payload):
        pass


def get_handler():
    with Connection(cfg.CONF.messaging.url) as conn:
        return FakeMessageHandler(conn, [FAKE_WORK_Q])


class QueueConsumerTest(DbTestCase):

    @mock.patch.object(FakeMessageHandler, 'process', mock.MagicMock())
    def test_process_message(self):
        payload = FakeModelDB()
        handler = get_handler()
        handler._queue_consumer._process_message(payload)
        FakeMessageHandler.process.assert_called_once_with(payload)

    @mock.patch.object(FakeMessageHandler, 'process', mock.MagicMock())
    def test_process_message_wrong_payload_type(self):
        payload = 100
        handler = get_handler()
        handler._queue_consumer._process_message(payload)
        self.assertFalse(FakeMessageHandler.process.called)
