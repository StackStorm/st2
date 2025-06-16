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

from st2common.util.monkey_patch import monkey_patch

monkey_patch()

import ssl
import random

import unittest
import eventlet

from bson.objectid import ObjectId
from kombu.mixins import ConsumerMixin
from oslo_config import cfg

from st2common.transport.publishers import PoolPublisher
from st2common.transport.utils import _get_ssl_kwargs
from st2common.transport import utils as transport_utils
from st2common.transport.kombu import Exchange, Queue
from st2common.models.db.liveaction import LiveActionDB

__all__ = ["TransportUtilsTestCase"]


class QueueConsumer(ConsumerMixin):
    def __init__(self, connection, queue):
        self.connection = connection
        self.queue = queue

        self.received_messages = []

    def get_consumers(self, Consumer, channel):
        return [
            Consumer(
                queues=[self.queue], accept=["pickle"], callbacks=[self.process_task]
            )
        ]

    def process_task(self, body, message):
        self.received_messages.append((body, message))
        message.ack()


class TransportUtilsTestCase(unittest.TestCase):
    def tearDown(self):
        super(TransportUtilsTestCase, self).tearDown()
        cfg.CONF.set_override(name="compression", group="messaging", override=None)

    def test_publish_compression(self):
        live_action_db = LiveActionDB()
        live_action_db.id = ObjectId()
        live_action_db.status = "succeeded"
        live_action_db.action = "core.local"
        live_action_db.result = {"foo": "bar"}

        exchange = Exchange("st2.execution.test", type="topic")
        queue_name = f"st2.test-{random.randint(1, 10000)}"
        queue = Queue(
            name=queue_name, exchange=exchange, routing_key="#", auto_delete=True
        )
        publisher = PoolPublisher()

        with transport_utils.get_connection() as connection:
            connection.connect()
            watcher = QueueConsumer(connection=connection, queue=queue)
            watcher_thread = eventlet.greenthread.spawn(watcher.run)

        # Give it some time to start up since we are publishing on a new queue
        eventlet.sleep(0.5)

        self.assertEqual(len(watcher.received_messages), 0)

        # 1. Verify compression is off as a default
        publisher.publish(payload=live_action_db, exchange=exchange)
        eventlet.sleep(0.2)

        self.assertEqual(len(watcher.received_messages), 1)
        self.assertEqual(
            watcher.received_messages[0][1].properties["content_type"],
            "application/x-python-serialize",
        )
        self.assertEqual(
            watcher.received_messages[0][1].properties["content_encoding"], "binary"
        )
        self.assertEqual(
            watcher.received_messages[0][1].properties["application_headers"], {}
        )
        self.assertEqual(watcher.received_messages[0][0].id, live_action_db.id)

        # 2. Verify config level option is used
        cfg.CONF.set_override(name="compression", group="messaging", override="zstd")
        publisher.publish(payload=live_action_db, exchange=exchange)

        eventlet.sleep(0.2)

        self.assertEqual(len(watcher.received_messages), 2)
        self.assertEqual(
            watcher.received_messages[1][1].properties["content_type"],
            "application/x-python-serialize",
        )
        self.assertEqual(
            watcher.received_messages[1][1].properties["content_encoding"], "binary"
        )
        self.assertEqual(
            watcher.received_messages[1][1].properties["application_headers"],
            {"compression": "application/zstd"},
        )
        self.assertEqual(watcher.received_messages[1][0].id, live_action_db.id)

        # 2. Verify argument level option is used and has precedence over config one
        cfg.CONF.set_override(name="compression", group="messaging", override="zstd")
        publisher.publish(payload=live_action_db, exchange=exchange, compression="gzip")

        eventlet.sleep(0.2)

        self.assertEqual(len(watcher.received_messages), 3)
        self.assertEqual(
            watcher.received_messages[2][1].properties["content_type"],
            "application/x-python-serialize",
        )
        self.assertEqual(
            watcher.received_messages[2][1].properties["content_encoding"], "binary"
        )
        self.assertEqual(
            watcher.received_messages[2][1].properties["application_headers"],
            {"compression": "application/x-gzip"},
        )
        self.assertEqual(watcher.received_messages[2][0].id, live_action_db.id)

        watcher_thread.kill()

    def test_get_ssl_kwargs(self):
        # 1. No SSL kwargs provided
        ssl_kwargs = _get_ssl_kwargs()
        self.assertEqual(ssl_kwargs, {})

        # 2. ssl kwarg provided
        ssl_kwargs = _get_ssl_kwargs(ssl=True)
        self.assertEqual(ssl_kwargs, {"ssl": True})

        # 3. ssl_keyfile provided
        ssl_kwargs = _get_ssl_kwargs(ssl_keyfile="/tmp/keyfile")
        self.assertEqual(ssl_kwargs, {"ssl": True, "keyfile": "/tmp/keyfile"})

        # 4. ssl_certfile provided
        ssl_kwargs = _get_ssl_kwargs(ssl_certfile="/tmp/certfile")
        self.assertEqual(ssl_kwargs, {"ssl": True, "certfile": "/tmp/certfile"})

        # 5. ssl_ca_certs provided
        ssl_kwargs = _get_ssl_kwargs(ssl_ca_certs="/tmp/ca_certs")
        self.assertEqual(ssl_kwargs, {"ssl": True, "ca_certs": "/tmp/ca_certs"})

        # 6. ssl_ca_certs and ssl_cert_reqs combinations
        ssl_kwargs = _get_ssl_kwargs(ssl_ca_certs="/tmp/ca_certs", ssl_cert_reqs="none")
        self.assertEqual(
            ssl_kwargs,
            {"ssl": True, "ca_certs": "/tmp/ca_certs", "cert_reqs": ssl.CERT_NONE},
        )

        ssl_kwargs = _get_ssl_kwargs(
            ssl_ca_certs="/tmp/ca_certs", ssl_cert_reqs="optional"
        )
        self.assertEqual(
            ssl_kwargs,
            {"ssl": True, "ca_certs": "/tmp/ca_certs", "cert_reqs": ssl.CERT_OPTIONAL},
        )

        ssl_kwargs = _get_ssl_kwargs(
            ssl_ca_certs="/tmp/ca_certs", ssl_cert_reqs="required"
        )
        self.assertEqual(
            ssl_kwargs,
            {"ssl": True, "ca_certs": "/tmp/ca_certs", "cert_reqs": ssl.CERT_REQUIRED},
        )
