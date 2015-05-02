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

from kombu import Connection
from kombu.mixins import ConsumerMixin
from oslo.config import cfg

from st2actions.container.base import RunnerContainer
from st2common import log as logging
from st2common.constants import action as action_constants
from st2common.services import action as action_service
from st2common.transport import liveaction, publishers
from st2common.util.greenpooldispatch import BufferedDispatcher


LOG = logging.getLogger(__name__)

ACTIONRUNNER_QUEUES = {
    'schedule': liveaction.get_queue('st2.actionrunner.req', routing_key=publishers.CREATE_RK),
    'execute': liveaction.get_queue('st2.actionrunner.work',
                                    routing_key=action_constants.LIVEACTION_STATUS_SCHEDULED)
}


class Worker(ConsumerMixin):

    def __init__(self, connection):
        self.connection = connection
        self.container = RunnerContainer()
        self._dispatcher = BufferedDispatcher()

    def shutdown(self):
        self._dispatcher.shutdown()

    def get_consumers(self, Consumer, channel):
        consumers = [
            Consumer(queues=[ACTIONRUNNER_QUEUES['schedule']],
                     accept=['pickle'],
                     callbacks=[self.schedule_request]),
            Consumer(queues=[ACTIONRUNNER_QUEUES['execute']],
                     accept=['pickle'],
                     callbacks=[self.execute_request])
        ]

        # use prefetch_count=1 for fair dispatch. This way workers that finish an item get the next
        # task and the work does not get queued behind any single large item.
        [consumer.qos(prefetch_count=1) for consumer in consumers]

        return consumers

    def _schedule_request(self, body):
        try:
            action_service.schedule(body)
        except Exception:
            LOG.exception('Scheduling of action execution failed. Message body : %s', body)

    def schedule_request(self, body, message):
        try:
            self._dispatcher.dispatch(self._schedule_request, body)
        finally:
            message.ack()

    def _execute_request(self, body):
        try:
            action_service.execute(body, self.container)
        except Exception:
            LOG.exception('Action execution failed. Message body : %s', body)

    def execute_request(self, body, message):
        try:
            self._dispatcher.dispatch(self._execute_request, body)
        finally:
            message.ack()


def work():
    with Connection(cfg.CONF.messaging.url) as conn:
        worker = Worker(conn)
        try:
            worker.run()
        except:
            worker.shutdown()
            raise
