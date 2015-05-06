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

import abc
import eventlet
import six

from kombu.mixins import ConsumerMixin

from st2common import log as logging
from st2common.util.greenpooldispatch import BufferedDispatcher


LOG = logging.getLogger(__name__)


class QueueConsumer(ConsumerMixin):
    def __init__(self, connection, queues, handler):
        self.connection = connection
        self._dispatcher = BufferedDispatcher()
        self._queues = queues
        self._handler = handler

    def shutdown(self):
        self._dispatcher.shutdown()

    def get_consumers(self, Consumer, channel):
        consumer = Consumer(queues=self._queues, accept=['pickle'], callbacks=[self.process])

        # use prefetch_count=1 for fair dispatch. This way workers that finish an item get the next
        # task and the work does not get queued behind any single large item.
        consumer.qos(prefetch_count=1)

        return [consumer]

    def process(self, body, message):
        try:
            self._dispatcher.dispatch(self._process_message, body)
        finally:
            message.ack()

    def _process_message(self, body):
        try:
            self._handler.process(body)
        except:
            LOG.exception('%s failed to process message: %s', self.__class__.__name__, body)


@six.add_metaclass(abc.ABCMeta)
class MessageHandler(object):
    def __init__(self, connection, queues):
        self._queue_consumer = QueueConsumer(connection, queues, self)
        self._consumer_thread = None

    def start(self, wait=False):
        LOG.info('Starting %s...', self.__class__.__name__)
        self._consumer_thread = eventlet.spawn(self._queue_consumer.run)

        if wait:
            self.wait()

    def wait(self):
        self._consumer_thread.wait()

    def shutdown(self):
        LOG.info('Shutting down %s...', self.__class__.__name__)
        self._queue_consumer.shutdown()

    @abc.abstractmethod
    def process(self, message):
        pass
