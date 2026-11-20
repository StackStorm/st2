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
from st2common.util import concurrency
from st2common.util import greenpooldispatch
from st2common.util.greenpooldispatch import BufferedDispatcher
from st2tests.base import DbTestCase
from tests.unit.base import FakeModelDB


# AMQP connection is mocked, so these do not need messaging.prefix
FAKE_XCHG = Exchange("st2.tests", type="topic")
FAKE_WORK_Q = Queue("st2.tests.unit", FAKE_XCHG)


def wait_for(condition, timeout=5):
    waited = 0
    while not condition() and waited < timeout:
        concurrency.sleep(0.01)
        waited += 0.01
    return condition()


class FakeMessageHandler(consumers.MessageHandler):
    message_type = FakeModelDB

    def process(self, payload):
        pass


class FakeConcurrencyOneMessageHandler(FakeMessageHandler):
    def get_concurrency(self):
        return 1


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

    def test_message_is_acked_before_processing(self):
        calls = []
        payload = FakeModelDB()
        handler = get_handler()
        mock_message = mock.MagicMock()
        mock_message.ack.side_effect = lambda: calls.append("ack")

        with mock.patch.object(
            FakeMessageHandler, "process", side_effect=lambda p: calls.append("process")
        ):
            handler._queue_consumer.process(payload, mock_message)
            self.assertTrue(wait_for(lambda: len(calls) == 2))

        self.assertEqual(calls, ["ack", "process"])

    def test_next_message_waits_for_free_slot(self):
        finish = []

        def process(payload):
            while not finish:
                concurrency.sleep(0.01)

        handler = FakeConcurrencyOneMessageHandler(mock.MagicMock(), [FAKE_WORK_Q])
        first_message = mock.MagicMock()
        second_message = mock.MagicMock()

        with mock.patch.object(
            FakeConcurrencyOneMessageHandler, "process", side_effect=process
        ):
            handler._queue_consumer.process(FakeModelDB(), first_message)
            self.assertTrue(first_message.ack.called)

            # The consumer callback blocks, so the second message is neither acked nor
            # processed while the first one is still running.
            second = concurrency.spawn(
                handler._queue_consumer.process, FakeModelDB(), second_message
            )
            concurrency.sleep(0.2)
            self.assertFalse(second_message.ack.called)
            self.assertEqual(FakeConcurrencyOneMessageHandler.process.call_count, 1)

            finish.append(True)
            concurrency.wait(second)
            self.assertTrue(second_message.ack.called)
            self.assertTrue(
                wait_for(
                    lambda: FakeConcurrencyOneMessageHandler.process.call_count == 2
                )
            )

    @mock.patch.object(greenpooldispatch, "SLOT_WAIT_INTERVAL_SECONDS", 0.01)
    def test_message_is_not_acked_on_shutdown(self):
        handler = FakeConcurrencyOneMessageHandler(mock.MagicMock(), [FAKE_WORK_Q])
        consumer = handler._queue_consumer
        self.assertTrue(consumer._dispatcher.acquire())

        mock_message = mock.MagicMock()
        waiting = concurrency.spawn(consumer.process, FakeModelDB(), mock_message)
        concurrency.sleep(0.05)

        consumer.shutdown()
        concurrency.wait(waiting)
        self.assertFalse(mock_message.ack.called)

    def test_concurrency_is_passed_to_dispatcher(self):
        handler = FakeConcurrencyOneMessageHandler(mock.MagicMock(), [FAKE_WORK_Q])
        self.assertEqual(handler._queue_consumer._dispatcher.free_count, 1)

        handler = get_handler()
        self.assertEqual(
            handler._queue_consumer._dispatcher.free_count,
            consumers.DEFAULT_CONCURRENCY,
        )


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

    @mock.patch.object(
        FakeStagedMessageHandler,
        "pre_ack_process",
        mock.MagicMock(side_effect=Exception("boom")),
    )
    @mock.patch.object(FakeStagedMessageHandler, "process", mock.MagicMock())
    def test_process_message_pre_ack_failure(self):
        payload = FakeModelDB()
        handler = get_staged_handler()
        mock_message = mock.MagicMock()
        handler._queue_consumer.process(payload, mock_message)
        self.assertTrue(mock_message.ack.called)
        self.assertFalse(FakeStagedMessageHandler.process.called)
        self.assertEqual(
            handler._queue_consumer._dispatcher.free_count,
            consumers.DEFAULT_CONCURRENCY,
        )

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
