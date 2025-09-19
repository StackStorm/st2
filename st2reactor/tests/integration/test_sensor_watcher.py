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

from time import monotonic

from pyrabbit.api import Client

from st2common.util import concurrency
from st2common.services.sensor_watcher import SensorWatcher
from st2tests.base import IntegrationTestCase

__all__ = ["SensorWatcherTestCase"]


class SensorWatcherTestCase(IntegrationTestCase):
    @classmethod
    def setUpClass(cls):
        super(SensorWatcherTestCase, cls).setUpClass()

    def setUp(self):
        super().setUp()
        # pre-condition: Make sure there is no test pollution
        # Delete any leftover queues from previous failed test runs
        self.rabbit_client = self._get_client()
        self._delete_sensor_watcher_amqp_queues(
            queue_name="st2.sensor.watch.covfefe", rabbit_client=self.rabbit_client
        )

        # Verify queues are deleted
        sw_queues = self._get_sensor_watcher_amqp_queues(
            queue_name="st2.sensor.watch.covfefe", rabbit_client=self.rabbit_client
        )
        self.assertTrue(len(sw_queues) == 0)

    def test_sensor_watch_queue_gets_deleted_on_stop(self):
        def create_handler(sensor_db):
            pass

        def update_handler(sensor_db):
            pass

        def delete_handler(sensor_db):
            pass

        sensor_watcher = SensorWatcher(
            create_handler, update_handler, delete_handler, queue_suffix="covfefe"
        )
        sensor_watcher.start()
        sw_queues = self._get_sensor_watcher_amqp_queues(
            queue_name="st2.sensor.watch.covfefe", rabbit_client=self.rabbit_client
        )

        start = monotonic()
        done = False
        while not done:
            concurrency.sleep(0.01)
            sw_queues = self._get_sensor_watcher_amqp_queues(
                queue_name="st2.sensor.watch.covfefe", rabbit_client=self.rabbit_client
            )
            done = len(sw_queues) > 0 or ((monotonic() - start) < 5)

        sensor_watcher.stop()
        sw_queues = self._get_sensor_watcher_amqp_queues(
            queue_name="st2.sensor.watch.covfefe", rabbit_client=self.rabbit_client
        )
        self.assertTrue(len(sw_queues) == 0)

    def _get_client(self):
        rabbit_client = Client("localhost:15672", "guest", "guest")
        return rabbit_client

    def _list_amqp_queues(self, rabbit_client):
        """
        :param rabbit_client: Client
        """
        queues = [q["name"] for q in rabbit_client.get_queues()]
        return queues

    def _get_sensor_watcher_amqp_queues(self, queue_name, rabbit_client):
        """
        :param rabbit_client: Client
        """
        all_queues = self._list_amqp_queues(rabbit_client)
        return set([q_name for q_name in all_queues if queue_name in q_name])

    def _delete_sensor_watcher_amqp_queues(self, queue_name, rabbit_client):
        """
        Delete all queues containing the specified queue_name pattern.

        :param string queue_name: Pattern to match in queue names
        :param rabbit_client: Client
        :returns: None
        """
        # Get all queues matching the pattern
        queues_to_delete = self._get_sensor_watcher_amqp_queues(
            queue_name=queue_name, rabbit_client=rabbit_client
        )

        if not queues_to_delete:
            return

        # Create a rabbit client and delete each queue
        for queue in queues_to_delete:
            # Use default vhost "/"
            rabbit_client.delete_queue("/", queue)
