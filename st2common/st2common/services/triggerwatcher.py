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
# pylint: disable=assignment-from-none

import eventlet
from kombu.mixins import ConsumerMixin
from kombu import Connection

from st2common import log as logging
from st2common.persistence.trigger import Trigger
from st2common.transport import reactor, publishers
from st2common.transport import utils as transport_utils
import st2common.util.queues as queue_utils

LOG = logging.getLogger(__name__)


class TriggerWatcher(ConsumerMixin):

    sleep_interval = 0  # sleep to co-operatively yield after processing each message

    def __init__(self, create_handler, update_handler, delete_handler,
                 trigger_types=None, queue_suffix=None, exclusive=False):
        """
        :param create_handler: Function which is called on TriggerDB create event.
        :type create_handler: ``callable``

        :param update_handler: Function which is called on TriggerDB update event.
        :type update_handler: ``callable``

        :param delete_handler: Function which is called on TriggerDB delete event.
        :type delete_handler: ``callable``

        :param trigger_types: If provided, handler function will only be called
                              if the trigger in the message payload is included
                              in this list.
        :type trigger_types: ``list``

        :param exclusive: If the Q is exclusive to a specific connection which is then
                          single connection created by TriggerWatcher. When the connection
                          breaks the Q is removed by the message broker.
        :type exclusive: ``bool``
        """
        # TODO: Handle trigger type filtering using routing key
        self._create_handler = create_handler
        self._update_handler = update_handler
        self._delete_handler = delete_handler
        self._trigger_types = trigger_types
        self._trigger_watch_q = self._get_queue(queue_suffix, exclusive=exclusive)

        self.connection = None
        self._load_thread = None
        self._updates_thread = None

        self._handlers = {
            publishers.CREATE_RK: create_handler,
            publishers.UPDATE_RK: update_handler,
            publishers.DELETE_RK: delete_handler
        }

    def get_consumers(self, Consumer, channel):
        return [Consumer(queues=[self._trigger_watch_q],
                         accept=['pickle'],
                         callbacks=[self.process_task])]

    def process_task(self, body, message):
        LOG.debug('process_task')
        LOG.debug('     body: %s', body)
        LOG.debug('     message.properties: %s', message.properties)
        LOG.debug('     message.delivery_info: %s', message.delivery_info)

        routing_key = message.delivery_info.get('routing_key', '')
        handler = self._handlers.get(routing_key, None)

        try:
            if not handler:
                LOG.debug('Skipping message %s as no handler was found.', message)
                return

            trigger_type = getattr(body, 'type', None)
            if self._trigger_types and trigger_type not in self._trigger_types:
                LOG.debug('Skipping message %s since\'t trigger_type doesn\'t match (type=%s)',
                          message, trigger_type)
                return

            try:
                handler(body)
            except Exception as e:
                LOG.exception('Handling failed. Message body: %s. Exception: %s',
                              body, e.message)
        finally:
            message.ack()

        eventlet.sleep(self.sleep_interval)

    def start(self):
        try:
            self.connection = Connection(transport_utils.get_messaging_urls())
            self._updates_thread = eventlet.spawn(self.run)
            self._load_thread = eventlet.spawn(self._load_triggers_from_db)
        except:
            LOG.exception('Failed to start watcher.')
            self.connection.release()

    def stop(self):
        try:
            self._updates_thread = eventlet.kill(self._updates_thread)
            self._load_thread = eventlet.kill(self._load_thread)
        finally:
            self.connection.release()

    # Note: We sleep after we consume a message so we give a chance to other
    # green threads to run. If we don't do that, ConsumerMixin will block on
    # waiting for a message on the queue.

    def on_consume_end(self, connection, channel):
        super(TriggerWatcher, self).on_consume_end(connection=connection,
                                                   channel=channel)
        eventlet.sleep(seconds=self.sleep_interval)

    def on_iteration(self):
        super(TriggerWatcher, self).on_iteration()
        eventlet.sleep(seconds=self.sleep_interval)

    def _load_triggers_from_db(self):
        for trigger_type in self._trigger_types:
            for trigger in Trigger.query(type=trigger_type):
                LOG.debug('Found existing trigger: %s in db.' % trigger)
                self._handlers[publishers.CREATE_RK](trigger)

    @staticmethod
    def _get_queue(queue_suffix, exclusive):
        queue_name = queue_utils.get_queue_name(queue_name_base='st2.trigger.watch',
                                                queue_name_suffix=queue_suffix,
                                                add_random_uuid_to_suffix=True
                                                )
        return reactor.get_trigger_cud_queue(queue_name, routing_key='#', exclusive=exclusive)
