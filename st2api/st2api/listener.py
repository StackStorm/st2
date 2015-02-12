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

from kombu import Connection, Queue
from kombu.mixins import ConsumerMixin
from oslo.config import cfg

from st2common.models.api.action import ActionExecutionAPI
from st2common.models.api.history import ActionExecutionHistoryAPI
from st2common.transport import actionexecution, history, publishers
from st2common import log as logging

__all__ = [
    'get_listener',
    'get_listener_if_set'
]

LOG = logging.getLogger(__name__)

QUEUE = Queue(None,
              actionexecution.ACTIONEXECUTION_XCHG,
              routing_key=publishers.ANY_RK,
              exclusive=True)

_listener = None


class Listener(ConsumerMixin):

    def __init__(self, connection):
        self.connection = connection
        self.queues = []
        self._stopped = False

    def get_consumers(self, consumer, channel):
        return [
            consumer(queues=[history.get_queue(routing_key=publishers.ANY_RK,
                                               exclusive=True)],
                     accept=['pickle'],
                     callbacks=[self.processor(ActionExecutionHistoryAPI)]),

            consumer(queues=[Queue(None,
                                   actionexecution.ACTIONEXECUTION_XCHG,
                                   routing_key=publishers.ANY_RK,
                                   exclusive=True)],
                     accept=['pickle'],
                     callbacks=[self.processor(ActionExecutionAPI)])
        ]

    def processor(self, model):
        def process(body, message):
            meta = message.delivery_info
            event_name = "%s__%s" % (meta.get('exchange'), meta.get('routing_key'))
            try:
                self.emit(event_name, model.from_model(body))
            finally:
                message.ack()

        return process

    def emit(self, event, body):
        pack = (event, body)
        for queue in self.queues:
            queue.put(pack)

    def generator(self):
        queue = eventlet.Queue()
        self.queues.append(queue)
        try:
            while not self._stopped:
                try:
                    yield queue.get(timeout=cfg.CONF.api.heartbeat)
                except eventlet.queue.Empty:
                    yield
        finally:
            self.queues.remove(queue)

    def shutdown(self):
        self._stopped = True


def listen(listener):
    try:
        listener.run()
    finally:
        listener.shutdown()


def get_listener():
    global _listener
    if not _listener:
        with Connection(cfg.CONF.messaging.url) as conn:
            _listener = Listener(conn)
            eventlet.spawn_n(listen, _listener)
    return _listener


def get_listener_if_set():
    global _listener
    return _listener
