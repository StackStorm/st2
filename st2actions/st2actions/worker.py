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
from st2common.constants.action import LIVEACTION_STATUS_RUNNING
from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED
from st2common.constants.action import LIVEACTION_STATUS_FAILED
from st2common.exceptions.actionrunner import ActionRunnerException
from st2common.services import executions
from st2common.transport import liveaction, publishers
from st2common.util import system_info
from st2common.util.action_db import (get_liveaction_by_id, update_liveaction_status)
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
        except Exception:
            LOG.exception('execute_action failed. Message body : %s', body)

    def execute_action(self, liveaction):
        # Note: We only want to execute actions which haven't completed yet
        if liveaction.status in [LIVEACTION_STATUS_SUCCEEDED, LIVEACTION_STATUS_FAILED]:
            LOG.info('Ignoring liveaction %s which has already finished', liveaction.id)
            return

        try:
            liveaction_db = get_liveaction_by_id(liveaction.id)
        except StackStormDBObjectNotFoundError:
            LOG.exception('Failed to find liveaction %s in the database.',
                          liveaction.id)
            raise
        # stamp liveaction with process_info
        runner_info = system_info.get_process_info()

        # Update liveaction status to "running"
        liveaction_db = update_liveaction_status(status=LIVEACTION_STATUS_RUNNING,
                                                 runner_info=runner_info,
                                                 liveaction_id=liveaction_db.id)
        action_execution_db = executions.update_execution(liveaction_db)

        # Launch action
        LOG.audit('Launching action execution.',
                  extra={'action_execution_id': str(action_execution_db.id),
                         'liveaction': liveaction_db.to_serializable_dict()})
        # the extra field will not be shown in non-audit logs so temporarily log at info.
        LOG.info('{~}action_execution: %s / {~}live_action: %s',
                 action_execution_db.id, liveaction_db.id)
        try:
            result = self.container.dispatch(liveaction_db)
            LOG.debug('Runner dispatch produced result: %s', result)
            if not result:
                raise ActionRunnerException('Failed to execute action.')
        except Exception:
            liveaction_db = update_liveaction_status(status=LIVEACTION_STATUS_FAILED,
                                                     liveaction_id=liveaction_db.id)
            raise

        return result


def work():
    with Connection(cfg.CONF.messaging.url) as conn:
        worker = Worker(conn)
        try:
            worker.run()
        except:
            worker.shutdown()
            raise
