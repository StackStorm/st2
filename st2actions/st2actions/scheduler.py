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
from st2common.constants import action as action_constants
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.persistence.action import LiveAction
from st2common.services import executions
from st2common.transport import liveaction, publishers
from st2common.util import action_db as action_utils
from st2common.util import system_info
from st2common.util.greenpooldispatch import BufferedDispatcher


LOG = logging.getLogger(__name__)

ACTIONRUNNER_REQUEST_Q = liveaction.get_queue('st2.actionrunner.req',
                                              routing_key=publishers.CREATE_RK)


class ActionSchedulerQueueConsumer(ConsumerMixin):
    def __init__(self, connection, handler):
        self.connection = connection
        self._dispatcher = BufferedDispatcher()
        self._handler = handler

    def shutdown(self):
        self._dispatcher.shutdown()

    def get_consumers(self, Consumer, channel):
        consumer = Consumer(queues=[ACTIONRUNNER_REQUEST_Q],
                            accept=['pickle'],
                            callbacks=[self.process_task])

        # use prefetch_count=1 for fair dispatch. This way workers that finish an item get the next
        # task and the work does not get queued behind any single large item.
        consumer.qos(prefetch_count=1)

        return [consumer]

    def process_task(self, body, message):
        try:
            self._dispatcher.dispatch(self._do_process_task, body)
        finally:
            message.ack()

    def _do_process_task(self, body):
        try:
            self._handler.process(body)
        except:
            LOG.exception('%s failed to process message: %s', self.__class__.__name__, body)


class ActionExecutionScheduler(object):
    def __init__(self, q_connection=None):
        self._queue_consumer = ActionSchedulerQueueConsumer(q_connection, self)
        self._consumer_thread = None

    def start(self):
        LOG.info('Starting %s...', self.__class__.__name__)
        self._consumer_thread = eventlet.spawn(self._queue_consumer.run)

    def wait(self):
        self._consumer_thread.wait()

    def shutdown(self):
        LOG.info('Shutting down %s...', self.__class__.__name__)
        self._queue_consumer.shutdown()

    def process(self, request):
        if request.status != action_constants.LIVEACTION_STATUS_REQUESTED:
            LOG.info('%s is ignoring %s (id=%s) with "%s" status.',
                     self.__class__.__name__, type(request), request.id, request.status)
            return

        try:
            liveaction_db = action_utils.get_liveaction_by_id(request.id)
        except StackStormDBObjectNotFoundError:
            LOG.exception('Failed to find liveaction %s in the database.', request.id)
            raise

        # stamp liveaction with process_info
        runner_info = system_info.get_process_info()

        # Update liveaction status to "scheduled"
        liveaction_db = action_utils.update_liveaction_status(
            status=action_constants.LIVEACTION_STATUS_SCHEDULED,
            runner_info=runner_info,
            liveaction_id=liveaction_db.id)

        action_execution_db = executions.update_execution(liveaction_db)

        extra = {'action_execution_db': action_execution_db, 'liveaction_db': liveaction_db}
        LOG.audit('Scheduled action execution.', extra=extra)

        # the extra field will not be shown in non-audit logs so temporarily log at info.
        LOG.info('Scheduled {~}action_execution: %s / {~}live_action: %s with "%s" status.',
                 action_execution_db.id, liveaction_db.id, request.status)

        LiveAction.publish_status(liveaction_db)


def get_scheduler():
    with Connection(cfg.CONF.messaging.url) as conn:
        return ActionExecutionScheduler(q_connection=conn)
