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

import sys
import traceback

from kombu import Connection

from st2actions.container.base import RunnerContainer
from st2common import log as logging
from st2common.constants import action as action_constants
from st2common.exceptions.actionrunner import ActionRunnerException
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.models.db.liveaction import LiveActionDB
from st2common.services import executions
from st2common.transport import consumers, liveaction
from st2common.transport import utils as transport_utils
from st2common.util import action_db as action_utils
from st2common.util import system_info


LOG = logging.getLogger(__name__)

ACTIONRUNNER_WORK_Q = liveaction.get_status_management_queue(
    'st2.actionrunner.work', routing_key=action_constants.LIVEACTION_STATUS_SCHEDULED)


class ActionExecutionDispatcher(consumers.MessageHandler):
    message_type = LiveActionDB

    def __init__(self, connection, queues):
        super(ActionExecutionDispatcher, self).__init__(connection, queues)
        self.container = RunnerContainer()

    def process(self, liveaction):
        """Dispatches the LiveAction to appropriate action runner.

        LiveAction in statuses other than "scheduled" are ignored. If
        LiveAction is already canceled and result is empty, the LiveAction
        is updated with a generic exception message.

        :param liveaction: Scheduled action execution request.
        :type liveaction: ``st2common.models.db.liveaction.LiveActionDB``

        :rtype: ``dict``
        """

        if liveaction.status == action_constants.LIVEACTION_STATUS_CANCELED:
            LOG.info('%s is not executing %s (id=%s) with "%s" status.',
                     self.__class__.__name__, type(liveaction), liveaction.id, liveaction.status)
            if not liveaction.result:
                updated_liveaction = action_utils.update_liveaction_status(
                    status=liveaction.status,
                    result={'message': 'Action execution canceled by user.'},
                    liveaction_id=liveaction.id)
                executions.update_execution(updated_liveaction)
            return

        if liveaction.status != action_constants.LIVEACTION_STATUS_SCHEDULED:
            LOG.info('%s is not executing %s (id=%s) with "%s" status.',
                     self.__class__.__name__, type(liveaction), liveaction.id, liveaction.status)
            return

        try:
            liveaction_db = action_utils.get_liveaction_by_id(liveaction.id)
        except StackStormDBObjectNotFoundError:
            LOG.exception('Failed to find liveaction %s in the database.', liveaction.id)
            raise

        # stamp liveaction with process_info
        runner_info = system_info.get_process_info()

        # Update liveaction status to "running"
        liveaction_db = action_utils.update_liveaction_status(
            status=action_constants.LIVEACTION_STATUS_RUNNING,
            runner_info=runner_info,
            liveaction_id=liveaction_db.id)

        action_execution_db = executions.update_execution(liveaction_db)

        # Launch action
        extra = {'action_execution_db': action_execution_db, 'liveaction_db': liveaction_db}
        LOG.audit('Launching action execution.', extra=extra)

        # the extra field will not be shown in non-audit logs so temporarily log at info.
        LOG.info('Dispatched {~}action_execution: %s / {~}live_action: %s with "%s" status.',
                 action_execution_db.id, liveaction_db.id, liveaction.status)

        return self._run_action(liveaction_db)

    def _run_action(self, liveaction_db):
        extra = {'liveaction_db': liveaction_db}
        try:
            result = self.container.dispatch(liveaction_db)
            LOG.debug('Runner dispatch produced result: %s', result)
            if not result:
                raise ActionRunnerException('Failed to execute action.')
        except:
            _, ex, tb = sys.exc_info()
            extra['error'] = str(ex)
            LOG.info('Action "%s" failed: %s' % (liveaction_db.action, str(ex)), extra=extra)

            liveaction_db = action_utils.update_liveaction_status(
                status=action_constants.LIVEACTION_STATUS_FAILED,
                liveaction_id=liveaction_db.id,
                result={'error': str(ex), 'traceback': ''.join(traceback.format_tb(tb, 20))})
            executions.update_execution(liveaction_db)
            raise

        return result


def get_worker():
    with Connection(transport_utils.get_messaging_urls()) as conn:
        return ActionExecutionDispatcher(conn, [ACTIONRUNNER_WORK_Q])
