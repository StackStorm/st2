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
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.constants.action import (ACTIONEXEC_STATUS_RUNNING, ACTIONEXEC_STATUS_FAILED)
from st2common.exceptions.actionrunner import ActionRunnerException
from st2common.transport import liveaction, publishers
from st2common.util.action_db import (get_actionexec_by_id, update_actionexecution_status)
from st2common.util.greenpooldispatch import BufferedDispatcher

LOG = logging.getLogger(__name__)


ACTIONRUNNER_WORK_Q = liveaction.get_queue('st2.actionrunner.work',
                                           routing_key=publishers.CREATE_RK)


class Worker(ConsumerMixin):

    def __init__(self, connection):
        self.connection = connection
        self.container = RunnerContainer()
        self._dispatcher = BufferedDispatcher()

    def shutdown(self):
        self._dispatcher.shutdown()

    def get_consumers(self, Consumer, channel):
        consumer = Consumer(queues=[ACTIONRUNNER_WORK_Q],
                            accept=['pickle'],
                            callbacks=[self.process_task])
        # use prefetch_count=1 for fair dispatch. This way workers that finish an item get the next
        # task and the work does not get queued behind any single large item.
        consumer.qos(prefetch_count=1)
        return [consumer]

    def process_task(self, body, message):
        # LOG.debug('process_task')
        # LOG.debug('     body: %s', body)
        # LOG.debug('     message.properties: %s', message.properties)
        # LOG.debug('     message.delivery_info: %s', message.delivery_info)
        try:
            self._dispatcher.dispatch(self._do_process_task, body)
        finally:
            message.ack()

    def _do_process_task(self, body):
        try:
            self.execute_action(body)
        except:
            LOG.exception('execute_action failed. Message body : %s', body)

    def execute_action(self, liveaction):
        try:
            actionexec_db = get_actionexec_by_id(liveaction.id)
        except StackStormDBObjectNotFoundError:
            LOG.exception('Failed to find liveaction %s in the database.',
                          liveaction.id)
            raise

        # Update liveaction status to "running"
        actionexec_db = update_actionexecution_status(status=ACTIONEXEC_STATUS_RUNNING,
                                                      actionexec_id=actionexec_db.id)
        # Launch action
        LOG.audit('Launching action execution.',
                  extra={'actionexec': actionexec_db.to_serializable_dict()})

        try:
            result = self.container.dispatch(actionexec_db)
            LOG.debug('Runner dispatch produced result: %s', result)
        except Exception:
            actionexec_db = update_actionexecution_status(status=ACTIONEXEC_STATUS_FAILED,
                                                          actionexec_id=actionexec_db.id)
            raise

        if not result:
            raise ActionRunnerException('Failed to execute action.')

        return result


def work():
    with Connection(cfg.CONF.messaging.url) as conn:
        worker = Worker(conn)
        try:
            worker.run()
        except:
            worker.shutdown()
            raise
