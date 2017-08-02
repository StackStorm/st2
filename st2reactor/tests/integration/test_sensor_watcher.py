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

from pyrabbit.api import Client

from st2common.services.sensor_watcher import SensorWatcher
from st2tests.base import IntegrationTestCase

__all__ = [
    'SensorWatcherTestCase'
]


class SensorWatcherTestCase(IntegrationTestCase):

    @classmethod
    def setUpClass(cls):
        super(SensorWatcherTestCase, cls).setUpClass()

    def test_sensor_watch_queue_gets_deleted_on_stop(self):

        def create_handler(sensor_db):
            pass

        def update_handler(sensor_db):
            pass

        def delete_handler(sensor_db):
            pass

        sensor_watcher = SensorWatcher(create_handler, update_handler, delete_handler)
        sensor_watcher.start()
        queues = self._get_sensor_watcher_amqp_queues()

        self.assertTrue(len(queues) == 1)
        sensor_watcher.stop()
        queues = self._get_sensor_watcher_amqp_queues()
        self.assertTrue(len(queues) == 0)

    def _get_sensor_watcher_amqp_queues(self):
        rabbit_client = Client('localhost:15672', 'guest', 'guest')
        queues = [q['name'] for q in rabbit_client.get_queues()]
        return set(filter(lambda q_name: 'st2.sensor.watch' in q_name, queues))
