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
from kombu.message import Message
import mock
import unittest

from st2common.services.sensor_watcher import SensorWatcher
from st2common.models.db.sensor import SensorTypeDB
from st2common.transport.publishers import PoolPublisher

MOCK_SENSOR_DB = SensorTypeDB(name="foo", pack="test")


class SensorWatcherTests(unittest.TestCase):
    @mock.patch.object(Message, "ack", mock.MagicMock())
    @mock.patch.object(PoolPublisher, "publish", mock.MagicMock())
    def test_assert_handlers_called(self):
        handler_vars = {
            "create_handler_called": False,
            "update_handler_called": False,
            "delete_handler_called": False,
        }

        def create_handler(sensor_db):
            handler_vars["create_handler_called"] = True

        def update_handler(sensor_db):
            handler_vars["update_handler_called"] = True

        def delete_handler(sensor_db):
            handler_vars["delete_handler_called"] = True

        sensor_watcher = SensorWatcher(create_handler, update_handler, delete_handler)

        message = Message(None, delivery_info={"routing_key": "create"})
        sensor_watcher.process_task(MOCK_SENSOR_DB, message)
        self.assertTrue(
            handler_vars["create_handler_called"], "create handler should be called."
        )

        message = Message(None, delivery_info={"routing_key": "update"})
        sensor_watcher.process_task(MOCK_SENSOR_DB, message)
        self.assertTrue(
            handler_vars["update_handler_called"], "update handler should be called."
        )

        message = Message(None, delivery_info={"routing_key": "delete"})
        sensor_watcher.process_task(MOCK_SENSOR_DB, message)
        self.assertTrue(
            handler_vars["delete_handler_called"], "delete handler should be called."
        )
