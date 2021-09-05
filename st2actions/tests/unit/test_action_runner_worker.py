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
import random
import eventlet

from kombu import Exchange
from kombu import Queue
from unittest2 import TestCase
from mock import Mock

from st2common.transport.consumers import ActionsQueueConsumer
from st2common.transport.publishers import PoolPublisher
from st2common.transport import utils as transport_utils
from st2common.models.db.liveaction import LiveActionDB

from st2tests import config as test_config

test_config.parse_args()

__all__ = ["ActionsQueueConsumerTestCase"]


class ActionsQueueConsumerTestCase(TestCase):
    message_count = 0
    message_type = LiveActionDB

    def test_process_right_dispatcher_is_used(self):
        handler = Mock()
        handler.message_type = LiveActionDB
        consumer = ActionsQueueConsumer(connection=None, queues=None, handler=handler)

        # Non-workflow action
        consumer._workflows_dispatcher = Mock()
        consumer._actions_dispatcher = Mock()

        body = LiveActionDB(
            status="scheduled", action="core.local", action_is_workflow=False
        )
        message = Mock()
        consumer.process(body=body, message=message)

        self.assertEqual(consumer._workflows_dispatcher.dispatch.call_count, 0)
        self.assertEqual(consumer._actions_dispatcher.dispatch.call_count, 1)

        # Workflow action
        consumer._workflows_dispatcher = Mock()
        consumer._actions_dispatcher = Mock()

        body = LiveActionDB(
            status="scheduled", action="core.local", action_is_workflow=True
        )
        message = Mock()
        consumer.process(body=body, message=message)

        self.assertEqual(consumer._workflows_dispatcher.dispatch.call_count, 1)
        self.assertEqual(consumer._actions_dispatcher.dispatch.call_count, 0)

    def test_stop_consumption_on_shutdown(self):
        exchange = Exchange("st2.execution.test", type="topic")
        queue_name = "test-" + str(random.randint(1, 10000))
        queue = Queue(
            name=queue_name, exchange=exchange, routing_key="#", auto_delete=True
        )
        publisher = PoolPublisher()
        with transport_utils.get_connection() as connection:
            connection.connect()
            watcher = ActionsQueueConsumer(
                connection=connection, queues=queue, handler=self
            )
            watcher_thread = eventlet.greenthread.spawn(watcher.run)

        # Give it some time to start up since we are publishing on a new queue
        eventlet.sleep(0.5)
        body = LiveActionDB(
            status="scheduled", action="core.local", action_is_workflow=False
        )
        publisher.publish(payload=body, exchange=exchange)
        eventlet.sleep(0.2)
        self.assertEqual(self.message_count, 1)
        body = LiveActionDB(
            status="scheduled", action="core.local", action_is_workflow=True
        )
        watcher.shutdown()
        eventlet.sleep(1)
        publisher.publish(payload=body, exchange=exchange)
        # Second published message won't be consumed.
        self.assertEqual(self.message_count, 1)
        watcher_thread.kill()

    def process(self, liveaction):
        self.message_count = self.message_count + 1
