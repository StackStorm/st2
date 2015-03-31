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

import eventlet
from kombu import Connection
from kombu.mixins import ConsumerMixin
from oslo.config import cfg

from st2common import log as logging
from st2common.transport import liveaction, publishers
from st2common.util.greenpooldispatch import BufferedDispatcher

LOG = logging.getLogger(__name__)

ACTIONUPDATE_WORK_Q = liveaction.get_queue('st2.notifiers.work',
                                           routing_key=publishers.UPDATE_RK)


class LiveActionUpdateQueueConsumer(ConsumerMixin):
    def __init__(self, connection, notifier):
        self.connection = connection
        self._dispatcher = BufferedDispatcher()
        self._notifier = notifier

    def shutdown(self):
        self._dispatcher.shutdown()

    def get_consumers(self, Consumer, channel):
        consumer = Consumer(queues=[ACTIONUPDATE_WORK_Q],
                            accept=['pickle'],
                            callbacks=[self.process_task])
        # use prefetch_count=1 for fair dispatch. This way workers that finish an item get the next
        # task and the work does not get queued behind any single large item.
        consumer.qos(prefetch_count=1)
        return [consumer]

    def process_task(self, body, message):
        LOG.debug('process_task')
        LOG.debug('     body: %s', body)
        LOG.debug('     message.properties: %s', message.properties)
        LOG.debug('     message.delivery_info: %s', message.delivery_info)
        try:
            self._dispatcher.dispatch(self._do_process_task, body)
        finally:
            message.ack()

    def _do_process_task(self, body):
        try:
            # XXX: Check if action status is complete and then call this method
            self._notifier.handle_action_complete(body)
        except:
            LOG.exception('Add query_context failed. Message body : %s', body)


class Notifier(object):
    def __init__(self, q_connection=None):
        self._queue_consumer = LiveActionUpdateQueueConsumer(q_connection, self)
        self._consumer_thread = None

    def start(self):
        self._consumer_thread = eventlet.spawn(self._queue_consumer.run)
        self._consumer_thread.wait()

    def handle_action_complete(self, liveaction):
        print(liveaction)


def get_notifier():
    with Connection(cfg.CONF.messaging.url) as conn:
        notifier = Notifier(q_connection=conn)
        return notifier
