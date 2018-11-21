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
import eventlet

from st2common import log as logging
from st2common.util import date
from st2common.constants import action as action_constants
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.models.db.liveaction import LiveActionDB
from st2common.services import action as action_service
from st2common.services import policies as policy_service
from st2common.persistence.liveaction import LiveAction
from st2common.persistence.execution_queue import ExecutionQueue
from st2common.util import action_db as action_utils
from st2common.services import coordination
from st2common.metrics import base as metrics
from st2common.exceptions import db as db_exc

__all__ = [
    'ExecutionQueueHandler',
    'get_handler'
]


LOG = logging.getLogger(__name__)


def _next_execution():
    """
        Sort executions by fifo and priority and get the latest, highest priority
        item from the queue and pop it off.
    """
    query = {
        "scheduled_start_timestamp__lte": date.get_datetime_utc_now(),
        "handling": False,
        "limit": 1,
        "order_by": [
            "scheduled_start_timestamp",
        ]
    }

    execution = ExecutionQueue.query(**query).first()
    if execution:
        execution.handling = True
        try:
            ExecutionQueue.add_or_update(execution, publish=False)
            return execution
        except db_exc.StackStormDBObjectWriteConflictError:
            LOG.info("Execution handled by another scheduler: %s", execution.id)

    return None


class ExecutionQueueHandler(object):
    def __init__(self):
        self.message_type = LiveActionDB
        self._shutdown = False
        self._pool = eventlet.GreenPool(size=10)

    def garbageCollection(self):
        LOG.debug('Starting scheduler garbage collection')

        while self._shutdown is not True:
            eventlet.greenthread.sleep(5)
            query = {
                "scheduled_start_timestamp__lte": date.append_milliseconds_to_time(
                    date.get_datetime_utc_now(),
                    -60000
                ),
                "handling": True,
            }

            executions = ExecutionQueue.query(**query)
            if executions:
                for execution in executions:
                    execution.handling = False
                    try:
                        ExecutionQueue.add_or_update(execution, publish=False)
                    except db_exc.StackStormDBObjectWriteConflictError:
                        LOG.info(
                            "Execution updated before rescheduling: %s",
                            execution.id
                        )

    def loop(self):
        LOG.debug('Entering scheduler loop')

        while self._shutdown is not True:
            eventlet.greenthread.sleep(0.1)
            with metrics.Timer(key='scheduler.loop'):
                execution = _next_execution()
            with metrics.Timer(key='scheduler.loop.spawn_execution'):
                if execution:
                    self._pool.spawn(self._handle_execution, execution)

    @metrics.CounterWithTimer(key='scheduler.handle_execution')
    def _handle_execution(self, execution, metrics_timer=None):
        LOG.info('Scheduling liveaction: %s', execution.liveaction)

        try:
            liveaction_db = action_utils.get_liveaction_by_id(execution.liveaction)
        except StackStormDBObjectNotFoundError:
            LOG.exception('Failed to find liveaction %s in the database.', execution.liveaction)
            ExecutionQueue.delete(execution)
            raise

        liveaction_db = self._apply_pre_run(liveaction_db, execution)

        if liveaction_db:
            if not self._exit_if_not_runnable(liveaction_db, execution):
                self._update_to_scheduled(liveaction_db, execution)

    @staticmethod
    def _apply_pre_run(liveaction_db, execution):
        # Apply policies defined for the action.
        liveaction_db = policy_service.apply_pre_run_policies(liveaction_db)

        LOG.info("Liveaction Status Pre-Run: %s", liveaction_db.status)

        if liveaction_db.status is action_constants.LIVEACTION_STATUS_POLICY_DELAYED:
            liveaction_db = action_service.update_status(
                liveaction_db, action_constants.LIVEACTION_STATUS_DELAYED, publish=False
            )
            execution.scheduled_start_timestamp = date.append_milliseconds_to_time(
                date.get_datetime_utc_now(),
                500
            )
            try:
                ExecutionQueue.add_or_update(execution, publish=False)
            except db_exc.StackStormDBObjectWriteConflictError:
                LOG.warning(
                    "Execution update conflict during scheduling: %s",
                    execution.id
                )

            return None

        if (liveaction_db.status in action_constants.LIVEACTION_COMPLETED_STATES or
                liveaction_db.status in action_constants.LIVEACTION_CANCEL_STATES):
            ExecutionQueue.delete(execution)
            return None

        return liveaction_db

    def _exit_if_not_runnable(self, liveaction_db, execution):
        # Exit if the status of the request is no longer runnable.
        # The status could have be changed by one of the policies.
        valid_status = [
            action_constants.LIVEACTION_STATUS_REQUESTED,
            action_constants.LIVEACTION_STATUS_SCHEDULED,
            action_constants.LIVEACTION_STATUS_DELAYED
        ]
        if liveaction_db.status not in valid_status:
            LOG.info(
                '%s is ignoring %s (id=%s) with "%s" status after policies are applied.',
                self.__class__.__name__,
                type(execution),
                execution.id,
                liveaction_db.status
            )
            ExecutionQueue.delete(execution)
            return True

        return False

    @staticmethod
    def _update_to_scheduled(liveaction_db, execution):
        # Update liveaction status to "scheduled".
        LOG.info("Liveaction Status Update to Scheduled 1: %s", liveaction_db.status)
        if liveaction_db.status in [action_constants.LIVEACTION_STATUS_REQUESTED,
                                    action_constants.LIVEACTION_STATUS_DELAYED]:
            liveaction_db = action_service.update_status(
                liveaction_db, action_constants.LIVEACTION_STATUS_SCHEDULED, publish=False)

        # Publish the "scheduled" status here manually. Otherwise, there could be a
        # race condition with the update of the action_execution_db if the execution
        # of the liveaction completes first.
        LiveAction.publish_status(liveaction_db)
        # Delete execution queue entry only after status is published.
        ExecutionQueue.delete(execution)
        LOG.info("Liveaction Status Update to Scheduled 2: %s", liveaction_db.status)

    def start(self):
        self._shutdown = False
        eventlet.spawn(self.loop)
        eventlet.spawn(self.garbageCollection)

    def shutdown(self):
        self._shutdown = True


def get_handler():
    return ExecutionQueueHandler()
