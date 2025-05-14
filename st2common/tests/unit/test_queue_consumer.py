# Copyright 2020 The StackStorm Authors.
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
import mock
from kombu import Exchange, Queue

from st2common.transport import consumers
from st2common.util.greenpooldispatch import BufferedDispatcher
from st2tests.base import DbTestCase
from tests.unit.base import FakeModelDB


# AMQP connection is mocked, so these do not need messaging.prefix
FAKE_XCHG = Exchange("st2.tests", type="topic")
FAKE_WORK_Q = Queue("st2.tests.unit", FAKE_XCHG)


class FakeMessageHandler(consumers.MessageHandler):
    message_type = FakeModelDB

    def process(self, payload):
        pass


def get_handler():
    return FakeMessageHandler(mock.MagicMock(), [FAKE_WORK_Q])


class QueueConsumerTest(DbTestCase):
    @mock.patch.object(FakeMessageHandler, "process", mock.MagicMock())
    def test_process_message(self):
        payload = FakeModelDB()
        handler = get_handler()
        handler._queue_consumer._process_message(payload)
        FakeMessageHandler.process.assert_called_once_with(payload)

    @mock.patch.object(FakeMessageHandler, "process", mock.MagicMock())
    def test_process_message_wrong_payload_type(self):
        payload = 100
        handler = get_handler()
        mock_message = mock.MagicMock()
        handler._queue_consumer.process(payload, mock_message)
        self.assertTrue(mock_message.ack.called)
        self.assertFalse(FakeMessageHandler.process.called)


class FakeStagedMessageHandler(consumers.StagedMessageHandler):
    message_type = FakeModelDB

    def pre_ack_process(self, message):
        return message

    def process(self, payload):
        pass


def get_staged_handler():
    return FakeStagedMessageHandler(mock.MagicMock(), [FAKE_WORK_Q])


class StagedQueueConsumerTest(DbTestCase):
    @mock.patch.object(FakeStagedMessageHandler, "pre_ack_process", mock.MagicMock())
    def test_process_message_pre_ack(self):
        payload = FakeModelDB()
        handler = get_staged_handler()
        mock_message = mock.MagicMock()
        handler._queue_consumer.process(payload, mock_message)
        FakeStagedMessageHandler.pre_ack_process.assert_called_once_with(payload)
        self.assertTrue(mock_message.ack.called)

    @mock.patch.object(BufferedDispatcher, "dispatch", mock.MagicMock())
    @mock.patch.object(FakeStagedMessageHandler, "process", mock.MagicMock())
    def test_process_message(self):
        payload = FakeModelDB()
        handler = get_staged_handler()
        mock_message = mock.MagicMock()
        handler._queue_consumer.process(payload, mock_message)
        BufferedDispatcher.dispatch.assert_called_once_with(
            handler._queue_consumer._process_message, payload
        )
        handler._queue_consumer._process_message(payload)
        FakeStagedMessageHandler.process.assert_called_once_with(payload)
        self.assertTrue(mock_message.ack.called)

    def test_process_message_wrong_payload_type(self):
        payload = 100
        handler = get_staged_handler()
        mock_message = mock.MagicMock()
        handler._queue_consumer.process(payload, mock_message)
        self.assertTrue(mock_message.ack.called)


class FakeVariableMessageHandler(consumers.VariableMessageHandler):
    def __init__(self, connection, queues):
        super(FakeVariableMessageHandler, self).__init__(connection, queues)

        self.message_types = {FakeModelDB: self.handle_fake_model}

    def process(self, message):
        handler_function = self.message_types.get(type(message))
        handler_function(message)

    def handle_fake_model(self, fk_db):
        pass


def get_variable_messages_handler():
    return FakeVariableMessageHandler(mock.MagicMock(), [FAKE_WORK_Q])


class VariableMessageQueueConsumerTest(DbTestCase):
    @mock.patch.object(
        FakeVariableMessageHandler, "handle_fake_model", mock.MagicMock()
    )
    def test_process_message(self):
        payload = FakeModelDB()
        handler = get_variable_messages_handler()
        handler._queue_consumer._process_message(payload)
        FakeVariableMessageHandler.handle_fake_model.assert_called_once_with(payload)

    @mock.patch.object(FakeVariableMessageHandler, "process", mock.MagicMock())
    def test_process_message_wrong_payload_type(self):
        payload = 100
        handler = get_variable_messages_handler()
        mock_message = mock.MagicMock()
        handler._queue_consumer.process(payload, mock_message)
        self.assertTrue(mock_message.ack.called)
        self.assertFalse(FakeVariableMessageHandler.process.called)
