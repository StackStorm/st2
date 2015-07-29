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

# XXX: This file has a lot of duplication with TriggerWatcher.
# XXX: Refactor.

import eventlet
import uuid
from kombu.mixins import ConsumerMixin
from kombu import Connection
from oslo_config import cfg

from st2common import log as logging
from st2common.transport import reactor, publishers
from st2common.transport import utils as transport_utils

LOG = logging.getLogger(__name__)


class SensorWatcher(ConsumerMixin):

    def __init__(self, create_handler, update_handler, delete_handler,
                 queue_suffix=None):
        """
        :param create_handler: Function which is called on SensorDB create event.
        :type create_handler: ``callable``

        :param update_handler: Function which is called on SensorDB update event.
        :type update_handler: ``callable``

        :param delete_handler: Function which is called on SensorDB delete event.
        :type delete_handler: ``callable``
        """
        # TODO: Handle sensor type filtering using routing key
        self._create_handler = create_handler
        self._update_handler = update_handler
        self._delete_handler = delete_handler
        self._sensor_watcher_q = self._get_queue(queue_suffix)

        self.connection = None
        self._updates_thread = None

        self._handlers = {
            publishers.CREATE_RK: create_handler,
            publishers.UPDATE_RK: update_handler,
            publishers.DELETE_RK: delete_handler
        }

    def get_consumers(self, Consumer, channel):
        consumers = [Consumer(queues=[self._sensor_watcher_q],
                              accept=['pickle'],
                              callbacks=[self.process_task])]
        return consumers

    def process_task(self, body, message):
        LOG.debug('process_task')
        LOG.debug('     body: %s', body)
        LOG.debug('     message.properties: %s', message.properties)
        LOG.debug('     message.delivery_info: %s', message.delivery_info)

        routing_key = message.delivery_info.get('routing_key', '')
        handler = self._handlers.get(routing_key, None)

        try:
            if not handler:
                LOG.info('Skipping message %s as no handler was found.', message)
                return

            try:
                handler(body)
            except Exception as e:
                LOG.exception('Handling failed. Message body: %s. Exception: %s',
                              body, e.message)
        finally:
            message.ack()

    def start(self):
        try:
            self.connection = Connection(transport_utils.get_messaging_urls())
            self._updates_thread = eventlet.spawn(self.run)
        except:
            LOG.exception('Failed to start sensor_watcher.')
            self.connection.release()

    def stop(self):
        try:
            if self._updates_thread:
                self._updates_thread = eventlet.kill(self._updates_thread)
        finally:
            if self.connection:
                self.connection.release()

    @staticmethod
    def _get_queue(queue_suffix):
        if not queue_suffix:
            # pick last 10 digits of uuid. Arbitrary but unique enough for the TriggerWatcher.
            u_hex = uuid.uuid4().hex
            queue_suffix = uuid.uuid4().hex[len(u_hex) - 10:]
        queue_name = 'st2.sensor.watch.%s' % queue_suffix
        return reactor.get_sensor_cud_queue(queue_name, routing_key='#')
