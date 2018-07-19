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

from __future__ import absolute_import
import sys
import traceback

from kombu import Connection

from st2actions.container.base import RunnerContainer
from st2common import log as logging
from st2common.constants import action as action_constants
from st2common.exceptions.actionrunner import ActionRunnerException
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.models.db.liveaction import LiveActionDB
from st2common.persistence.execution import ActionExecution
from st2common.services import executions
from st2common.services import workflows as wf_svc
from st2common.transport.consumers import MessageHandler
from st2common.transport.consumers import ActionsQueueConsumer
from st2common.transport import utils as transport_utils
from st2common.util import action_db as action_utils
from st2common.util import system_info
from st2common.transport import queues


__all__ = [
    'ActionExecutionDispatcher',
    'get_worker'
]


LOG = logging.getLogger(__name__)

ACTIONRUNNER_QUEUES = [
    queues.ACTIONRUNNER_WORK_QUEUE,
    queues.ACTIONRUNNER_CANCEL_QUEUE,
    queues.ACTIONRUNNER_PAUSE_QUEUE,
    queues.ACTIONRUNNER_RESUME_QUEUE
]

ACTIONRUNNER_DISPATCHABLE_STATES = [
    action_constants.LIVEACTION_STATUS_SCHEDULED,
    action_constants.LIVEACTION_STATUS_CANCELING,
    action_constants.LIVEACTION_STATUS_PAUSING,
    action_constants.LIVEACTION_STATUS_RESUMING
]


class ActionExecutionDispatcher(MessageHandler):
    message_type = LiveActionDB

    def __init__(self, connection, queues):
        super(ActionExecutionDispatcher, self).__init__(connection, queues)
        self.container = RunnerContainer()
        self._running_liveactions = set()

    def get_queue_consumer(self, connection, queues):
        # We want to use a special ActionsQueueConsumer which uses 2 dispatcher pools
        return ActionsQueueConsumer(connection=connection, queues=queues, handler=self)

    def process(self, liveaction):
        """Dispatches the LiveAction to appropriate action runner.

        LiveAction in statuses other than "scheduled" and "canceling" are ignored. If
        LiveAction is already canceled and result is empty, the LiveAction
        is updated with a generic exception message.

        :param liveaction: Action execution request.
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

        if liveaction.status not in ACTIONRUNNER_DISPATCHABLE_STATES:
            LOG.info('%s is not dispatching %s (id=%s) with "%s" status.',
                     self.__class__.__name__, type(liveaction), liveaction.id, liveaction.status)
            return

        try:
            liveaction_db = action_utils.get_liveaction_by_id(liveaction.id)
        except StackStormDBObjectNotFoundError:
            LOG.exception('Failed to find liveaction %s in the database.', liveaction.id)
            raise

        if liveaction.status != liveaction_db.status:
            LOG.warning(
                'The status of liveaction %s has changed from %s to %s '
                'while in the queue waiting for processing.',
                liveaction.id,
                liveaction.status,
                liveaction_db.status
            )

        dispatchers = {
            action_constants.LIVEACTION_STATUS_SCHEDULED: self._run_action,
            action_constants.LIVEACTION_STATUS_CANCELING: self._cancel_action,
            action_constants.LIVEACTION_STATUS_PAUSING: self._pause_action,
            action_constants.LIVEACTION_STATUS_RESUMING: self._resume_action
        }

        return dispatchers[liveaction.status](liveaction)

    def shutdown(self):
        super(ActionExecutionDispatcher, self).shutdown()
        # Abandon running executions if incomplete
        while self._running_liveactions:
            liveaction_id = self._running_liveactions.pop()
            try:
                executions.abandon_execution_if_incomplete(liveaction_id=liveaction_id)
            except:
                LOG.exception('Failed to abandon liveaction %s.', liveaction_id)

    def _run_action(self, liveaction_db):
        # stamp liveaction with process_info
        runner_info = system_info.get_process_info()

        # Update liveaction status to "running"
        liveaction_db = action_utils.update_liveaction_status(
            status=action_constants.LIVEACTION_STATUS_RUNNING,
            runner_info=runner_info,
            liveaction_id=liveaction_db.id)

        self._running_liveactions.add(liveaction_db.id)

        action_execution_db = executions.update_execution(liveaction_db)

        # Launch action
        extra = {'action_execution_db': action_execution_db, 'liveaction_db': liveaction_db}
        LOG.audit('Launching action execution.', extra=extra)

        # the extra field will not be shown in non-audit logs so temporarily log at info.
        LOG.info('Dispatched {~}action_execution: %s / {~}live_action: %s with "%s" status.',
                 action_execution_db.id, liveaction_db.id, liveaction_db.status)

        extra = {'liveaction_db': liveaction_db}
        try:
            result = self.container.dispatch(liveaction_db)
            LOG.debug('Runner dispatch produced result: %s', result)
            if not result and not liveaction_db.action_is_workflow:
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
        finally:
            # In the case of worker shutdown, the items are removed from _running_liveactions.
            # As the subprocesses for action executions are terminated, this finally block
            # will be executed. Set remove will result in KeyError if item no longer exists.
            # Use set discard to not raise the KeyError.
            self._running_liveactions.discard(liveaction_db.id)

        return result

    def _cancel_action(self, liveaction_db):
        action_execution_db = ActionExecution.get(liveaction__id=str(liveaction_db.id))
        extra = {'action_execution_db': action_execution_db, 'liveaction_db': liveaction_db}
        LOG.audit('Canceling action execution.', extra=extra)

        # the extra field will not be shown in non-audit logs so temporarily log at info.
        LOG.info('Dispatched {~}action_execution: %s / {~}live_action: %s with "%s" status.',
                 action_execution_db.id, liveaction_db.id, liveaction_db.status)

        try:
            result = self.container.dispatch(liveaction_db)
            LOG.debug('Runner dispatch produced result: %s', result)
        except:
            _, ex, tb = sys.exc_info()
            extra['error'] = str(ex)
            LOG.info('Failed to cancel action execution %s.' % (liveaction_db.id), extra=extra)
            raise

        return result

    def _pause_action(self, liveaction_db):
        action_execution_db = ActionExecution.get(liveaction__id=str(liveaction_db.id))
        extra = {'action_execution_db': action_execution_db, 'liveaction_db': liveaction_db}
        LOG.audit('Pausing action execution.', extra=extra)

        # the extra field will not be shown in non-audit logs so temporarily log at info.
        LOG.info('Dispatched {~}action_execution: %s / {~}live_action: %s with "%s" status.',
                 action_execution_db.id, liveaction_db.id, liveaction_db.status)

        try:
            result = self.container.dispatch(liveaction_db)
            LOG.debug('Runner dispatch produced result: %s', result)
        except:
            _, ex, tb = sys.exc_info()
            extra['error'] = str(ex)
            LOG.info('Failed to pause action execution %s.' % (liveaction_db.id), extra=extra)
            raise

        return result

    def _resume_action(self, liveaction_db):
        action_execution_db = ActionExecution.get(liveaction__id=str(liveaction_db.id))
        extra = {'action_execution_db': action_execution_db, 'liveaction_db': liveaction_db}
        LOG.audit('Resuming action execution.', extra=extra)

        # the extra field will not be shown in non-audit logs so temporarily log at info.
        LOG.info('Dispatched {~}action_execution: %s / {~}live_action: %s with "%s" status.',
                 action_execution_db.id, liveaction_db.id, liveaction_db.status)

        try:
            result = self.container.dispatch(liveaction_db)
            LOG.debug('Runner dispatch produced result: %s', result)
        except:
            _, ex, tb = sys.exc_info()
            extra['error'] = str(ex)
            LOG.info('Failed to resume action execution %s.' % (liveaction_db.id), extra=extra)
            raise

        # Cascade the resume upstream if action execution is child of an orchestra workflow.
        # The action service request_resume function is not used here because we do not want
        # other peer subworkflows to be resumed.
        if 'orchestra' in action_execution_db.context and 'parent' in action_execution_db.context:
            wf_svc.handle_action_execution_resume(action_execution_db)

        return result


def get_worker():
    with Connection(transport_utils.get_messaging_urls()) as conn:
        return ActionExecutionDispatcher(conn, ACTIONRUNNER_QUEUES)
