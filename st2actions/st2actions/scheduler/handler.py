# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
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
import retrying
from oslo_config import cfg

from st2common import log as logging
from st2common.util import date
from st2common.util import service as service_utils
from st2common.constants import action as action_constants
from st2common.constants import policy as policy_constants
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.models.db.liveaction import LiveActionDB
from st2common.services import action as action_service
from st2common.services import coordination as coordination_service
from st2common.services import executions as execution_service
from st2common.services import policies as policy_service
from st2common.persistence.execution import ActionExecution
from st2common.persistence.liveaction import LiveAction
from st2common.persistence.execution_queue import ActionExecutionSchedulingQueue
from st2common.util import action_db as action_utils
from st2common.metrics import base as metrics
from st2common.exceptions import db as db_exc

__all__ = ["ActionExecutionSchedulingQueueHandler", "get_handler"]


LOG = logging.getLogger(__name__)

# When a policy delayed execution is detected it will be try to be rescheduled by the scheduler
# again in this amount of milliseconds.
POLICY_DELAYED_EXECUTION_RESCHEDULE_TIME_MS = 2500


class ActionExecutionSchedulingQueueHandler(object):
    def __init__(self):
        self.message_type = LiveActionDB
        self._shutdown = False
        self._pool = eventlet.GreenPool(size=cfg.CONF.scheduler.pool_size)
        # If an ActionExecutionSchedulingQueueItemDB object hasn't been updated fore more than
        # this amount of milliseconds, it will be marked as "handled=False".
        # As soon as an item is picked by scheduler to be processed, it should be processed very
        # fast (< 5 seconds). If an item is still being marked as processing it likely indicates
        # that the scheduler process which was processing that item crashed or similar so we need
        # to mark it as "handling=False" so some other scheduler process can pick it up.
        self._execution_scheduling_timeout_threshold_ms = (
            cfg.CONF.scheduler.execution_scheduling_timeout_threshold_min * 60 * 1000
        )
        self._coordinator = coordination_service.get_coordinator(start_heart=True)
        self._main_thread = None
        self._cleanup_thread = None

    def run(self):
        LOG.debug("Starting scheduler handler...")

        while not self._shutdown:
            eventlet.greenthread.sleep(cfg.CONF.scheduler.sleep_interval)
            self.process()

    @retrying.retry(
        retry_on_exception=service_utils.retry_on_exceptions,
        stop_max_attempt_number=cfg.CONF.scheduler.retry_max_attempt,
        wait_fixed=cfg.CONF.scheduler.retry_wait_msec,
    )
    def process(self):
        execution_queue_item_db = self._get_next_execution()

        if execution_queue_item_db:
            self._pool.spawn(self._handle_execution, execution_queue_item_db)

    def cleanup(self):
        LOG.debug("Starting scheduler garbage collection...")

        while not self._shutdown:
            eventlet.greenthread.sleep(cfg.CONF.scheduler.gc_interval)
            self._handle_garbage_collection()

    def _reset_handling_flag(self):
        """
        Periodically look for executions which have "handling" set to "True" and haven't been
        updated for a while (this likely indicates that an execution as picked up by a scheduler
        process which died before finishing the processing or similar) and reset handling to
        False so other scheduler can pick it up.
        """
        query = {
            "scheduled_start_timestamp__lte": date.append_milliseconds_to_time(
                date.get_datetime_utc_now(),
                -self._execution_scheduling_timeout_threshold_ms,
            ),
            "handling": True,
        }

        execution_queue_item_dbs = ActionExecutionSchedulingQueue.query(**query) or []

        for execution_queue_item_db in execution_queue_item_dbs:
            execution_queue_item_db.handling = False

            try:
                ActionExecutionSchedulingQueue.add_or_update(
                    execution_queue_item_db, publish=False
                )
                LOG.info(
                    '[%s] Removing lock for orphaned execution queue item "%s".',
                    execution_queue_item_db.action_execution_id,
                    str(execution_queue_item_db.id),
                )
            except db_exc.StackStormDBObjectWriteConflictError:
                LOG.info(
                    '[%s] Execution queue item "%s" updated during garbage collection.',
                    execution_queue_item_db.action_execution_id,
                    str(execution_queue_item_db.id),
                )

    # TODO: Remove this function for fixing missing action_execution_id in v3.2.
    # A new field is added to ActionExecutionSchedulingQueue. This is a temporary patch
    # to populate the action_execution_id when empty.
    def _fix_missing_action_execution_id(self):
        """
        Auto-populate the action_execution_id in ActionExecutionSchedulingQueue if empty.
        """
        for entry in ActionExecutionSchedulingQueue.query(
            action_execution_id__in=["", None]
        ):
            execution_db = ActionExecution.get(liveaction__id=entry.liveaction_id)

            if not execution_db:
                continue

            msg = '[%s] Populating action_execution_id for item "%s".'
            LOG.info(msg, str(execution_db.id), str(entry.id))
            entry.action_execution_id = str(execution_db.id)
            ActionExecutionSchedulingQueue.add_or_update(entry, publish=False)

    # TODO: Remove this function for cleanup policy-delayed in v3.2.
    # This is a temporary cleanup to remove executions in deprecated policy-delayed status.
    def _cleanup_policy_delayed(self):
        """
        Clean up any action execution in the deprecated policy-delayed status. Associated
        entries in the scheduling queue will be removed and the action execution will be
        moved back into requested status.
        """

        policy_delayed_liveaction_dbs = LiveAction.query(status="policy-delayed") or []

        for liveaction_db in policy_delayed_liveaction_dbs:
            ex_que_qry = {"liveaction_id": str(liveaction_db.id), "handling": False}
            execution_queue_item_dbs = (
                ActionExecutionSchedulingQueue.query(**ex_que_qry) or []
            )

            for execution_queue_item_db in execution_queue_item_dbs:
                # Mark the entry in the scheduling queue for handling.
                try:
                    execution_queue_item_db.handling = True
                    execution_queue_item_db = (
                        ActionExecutionSchedulingQueue.add_or_update(
                            execution_queue_item_db, publish=False
                        )
                    )
                except db_exc.StackStormDBObjectWriteConflictError:
                    msg = (
                        '[%s] Item "%s" is currently being processed by another scheduler.'
                        % (
                            execution_queue_item_db.action_execution_id,
                            str(execution_queue_item_db.id),
                        )
                    )
                    LOG.error(msg)
                    raise Exception(msg)

                # Delete the entry from the scheduling queue.
                LOG.info(
                    '[%s] Removing policy-delayed entry "%s" from the scheduling queue.',
                    execution_queue_item_db.action_execution_id,
                    str(execution_queue_item_db.id),
                )

                ActionExecutionSchedulingQueue.delete(execution_queue_item_db)

                # Update the status of the liveaction and execution to requested.
                LOG.info(
                    '[%s] Removing policy-delayed entry "%s" from the scheduling queue.',
                    execution_queue_item_db.action_execution_id,
                    str(execution_queue_item_db.id),
                )

                liveaction_db = action_service.update_status(
                    liveaction_db, action_constants.LIVEACTION_STATUS_REQUESTED
                )

                execution_service.update_execution(liveaction_db)

    @retrying.retry(
        retry_on_exception=service_utils.retry_on_exceptions,
        stop_max_attempt_number=cfg.CONF.scheduler.retry_max_attempt,
        wait_fixed=cfg.CONF.scheduler.retry_wait_msec,
    )
    def _handle_garbage_collection(self):
        self._reset_handling_flag()

    # NOTE: This method call is intentionally not instrumented since it causes too much overhead
    # and noise under DEBUG log level
    def _get_next_execution(self):
        """
        Sort execution requests by FIFO and priority and get the latest, highest priority item from
        the queue and pop it off.

        NOTE: FIFO order is not guaranteed anymore for executions which are re-scheduled and delayed
        due to a policy.
        """
        query = {
            "scheduled_start_timestamp__lte": date.get_datetime_utc_now(),
            "handling": False,
            "limit": 1,
            "order_by": ["+scheduled_start_timestamp", "+original_start_timestamp"],
        }

        execution_queue_item_db = ActionExecutionSchedulingQueue.query(**query).first()

        if not execution_queue_item_db:
            return None

        # Mark that this scheduler process is currently handling (processing) that request
        # NOTE: This operation is atomic (CAS)
        msg = '[%s] Retrieved item "%s" from scheduling queue.'
        LOG.info(
            msg, execution_queue_item_db.action_execution_id, execution_queue_item_db.id
        )
        execution_queue_item_db.handling = True

        try:
            ActionExecutionSchedulingQueue.add_or_update(
                execution_queue_item_db, publish=False
            )
            return execution_queue_item_db
        except db_exc.StackStormDBObjectWriteConflictError:
            LOG.info(
                '[%s] Item "%s" is already handled by another scheduler.',
                execution_queue_item_db.action_execution_id,
                str(execution_queue_item_db.id),
            )

        return None

    @metrics.CounterWithTimer(key="scheduler.handle_execution")
    def _handle_execution(self, execution_queue_item_db):
        action_execution_id = str(execution_queue_item_db.action_execution_id)
        liveaction_id = str(execution_queue_item_db.liveaction_id)
        queue_item_id = str(execution_queue_item_db.id)
        extra = {"queue_item_id": queue_item_id}

        LOG.info(
            '[%s] Scheduling Liveaction "%s".',
            action_execution_id,
            liveaction_id,
            extra=extra,
        )

        try:
            liveaction_db = action_utils.get_liveaction_by_id(liveaction_id)
        except StackStormDBObjectNotFoundError:
            msg = '[%s] Failed to find liveaction "%s" in the database (queue_item_id=%s).'
            LOG.exception(
                msg, action_execution_id, liveaction_id, queue_item_id, extra=extra
            )
            ActionExecutionSchedulingQueue.delete(execution_queue_item_db)
            raise

        # Identify if the action has policies that require locking.
        action_has_policies_require_lock = policy_service.has_policies(
            liveaction_db, policy_types=policy_constants.POLICY_TYPES_REQUIRING_LOCK
        )

        # Acquire a distributed lock if the referenced action has specific policies attached.
        if action_has_policies_require_lock:
            # Warn users that the coordination service is not configured.
            if not coordination_service.configured():
                LOG.warning(
                    "[%s] Coordination backend is not configured. "
                    "Policy enforcement is best effort.",
                    action_execution_id,
                )

            # Acquire a distributed lock before querying the database to make sure that only one
            # scheduler is scheduling execution for this action. Even if the coordination service
            # is not configured, the fake driver using zake or the file driver can still acquire
            # a lock for the local process or server respectively.
            lock_uid = liveaction_db.action
            msg = '[%s] %s is attempting to acquire lock "%s".'
            LOG.debug(msg, action_execution_id, self.__class__.__name__, lock_uid)
            lock = self._coordinator.get_lock(lock_uid)

            try:
                if lock.acquire(blocking=False):
                    self._regulate_and_schedule(liveaction_db, execution_queue_item_db)
                else:
                    self._delay(liveaction_db, execution_queue_item_db)
            finally:
                lock.release()
        else:
            # Otherwise if there is no policy, then schedule away.
            self._schedule(liveaction_db, execution_queue_item_db)

    def _regulate_and_schedule(self, liveaction_db, execution_queue_item_db):
        action_execution_id = str(execution_queue_item_db.action_execution_id)
        liveaction_id = str(execution_queue_item_db.liveaction_id)
        queue_item_id = str(execution_queue_item_db.id)
        extra = {"queue_item_id": queue_item_id}

        LOG.info(
            '[%s] Liveaction "%s" has status "%s" before applying policies.',
            action_execution_id,
            liveaction_id,
            liveaction_db.status,
            extra=extra,
        )

        # Apply policies defined for the action.
        liveaction_db = policy_service.apply_pre_run_policies(liveaction_db)

        LOG.info(
            '[%s] Liveaction "%s" has status "%s" after applying policies.',
            action_execution_id,
            liveaction_id,
            liveaction_db.status,
            extra=extra,
        )

        if liveaction_db.status == action_constants.LIVEACTION_STATUS_DELAYED:
            LOG.info(
                '[%s] Liveaction "%s" is delayed and scheduling queue is updated.',
                action_execution_id,
                liveaction_id,
                extra=extra,
            )

            liveaction_db = action_service.update_status(
                liveaction_db, action_constants.LIVEACTION_STATUS_DELAYED, publish=False
            )

            execution_queue_item_db.handling = False
            execution_queue_item_db.scheduled_start_timestamp = (
                date.append_milliseconds_to_time(
                    date.get_datetime_utc_now(),
                    POLICY_DELAYED_EXECUTION_RESCHEDULE_TIME_MS,
                )
            )

            try:
                ActionExecutionSchedulingQueue.add_or_update(
                    execution_queue_item_db, publish=False
                )
            except db_exc.StackStormDBObjectWriteConflictError:
                LOG.warning(
                    "[%s] Database write conflict on updating scheduling queue.",
                    action_execution_id,
                    extra=extra,
                )

            return

        if (
            liveaction_db.status in action_constants.LIVEACTION_COMPLETED_STATES
            or liveaction_db.status in action_constants.LIVEACTION_CANCEL_STATES
        ):
            ActionExecutionSchedulingQueue.delete(execution_queue_item_db)
            return

        self._schedule(liveaction_db, execution_queue_item_db)

    def _delay(self, liveaction_db, execution_queue_item_db):
        action_execution_id = str(execution_queue_item_db.action_execution_id)
        liveaction_id = str(execution_queue_item_db.liveaction_id)
        queue_item_id = str(execution_queue_item_db.id)
        extra = {"queue_item_id": queue_item_id}

        LOG.info(
            '[%s] Liveaction "%s" is delayed and scheduling queue is updated.',
            action_execution_id,
            liveaction_id,
            extra=extra,
        )

        liveaction_db = action_service.update_status(
            liveaction_db, action_constants.LIVEACTION_STATUS_DELAYED, publish=False
        )

        execution_queue_item_db.scheduled_start_timestamp = (
            date.append_milliseconds_to_time(
                date.get_datetime_utc_now(), POLICY_DELAYED_EXECUTION_RESCHEDULE_TIME_MS
            )
        )

        try:
            execution_queue_item_db.handling = False
            ActionExecutionSchedulingQueue.add_or_update(
                execution_queue_item_db, publish=False
            )
        except db_exc.StackStormDBObjectWriteConflictError:
            LOG.warning(
                "[%s] Database write conflict on updating scheduling queue.",
                action_execution_id,
                extra=extra,
            )

    def _schedule(self, liveaction_db, execution_queue_item_db):
        if self._is_execution_queue_item_runnable(
            liveaction_db, execution_queue_item_db
        ):
            self._update_to_scheduled(liveaction_db, execution_queue_item_db)

    @staticmethod
    def _is_execution_queue_item_runnable(liveaction_db, execution_queue_item_db):
        """
        Return True if a particular execution request is runnable.

        The status of the liveaction could have been changed by one of the policies and that could
        make execution not runnable anymore.
        """
        valid_status = [
            action_constants.LIVEACTION_STATUS_REQUESTED,
            action_constants.LIVEACTION_STATUS_SCHEDULED,
            action_constants.LIVEACTION_STATUS_DELAYED,
        ]

        if liveaction_db.status in valid_status:
            return True

        action_execution_id = str(execution_queue_item_db.action_execution_id)
        liveaction_id = str(execution_queue_item_db.liveaction_id)
        queue_item_id = str(execution_queue_item_db.id)
        extra = {"queue_item_id": queue_item_id}

        LOG.info(
            '[%s] Ignoring Liveaction "%s" with status "%s" after policies are applied.',
            action_execution_id,
            liveaction_id,
            liveaction_db.status,
            extra=extra,
        )

        ActionExecutionSchedulingQueue.delete(execution_queue_item_db)

        return False

    @staticmethod
    def _update_to_scheduled(liveaction_db, execution_queue_item_db):
        action_execution_id = str(execution_queue_item_db.action_execution_id)
        liveaction_id = str(execution_queue_item_db.liveaction_id)
        queue_item_id = str(execution_queue_item_db.id)
        extra = {"queue_item_id": queue_item_id}

        # Update liveaction status to "scheduled".
        LOG.info(
            '[%s] Liveaction "%s" with status "%s" is updated to status "scheduled."',
            action_execution_id,
            liveaction_id,
            liveaction_db.status,
            extra=extra,
        )

        if liveaction_db.status in [
            action_constants.LIVEACTION_STATUS_REQUESTED,
            action_constants.LIVEACTION_STATUS_DELAYED,
        ]:
            liveaction_db = action_service.update_status(
                liveaction_db,
                action_constants.LIVEACTION_STATUS_SCHEDULED,
                publish=False,
            )

        # Publish the "scheduled" status here manually. Otherwise, there could be a
        # race condition with the update of the action_execution_db if the execution
        # of the liveaction completes first.
        LiveAction.publish_status(liveaction_db)

        # Delete execution queue entry only after status is published.
        ActionExecutionSchedulingQueue.delete(execution_queue_item_db)

    def start(self):
        self._shutdown = False

        # Spawn the worker threads.
        self._main_thread = eventlet.spawn(self.run)
        self._cleanup_thread = eventlet.spawn(self.cleanup)

        # Link the threads to the shutdown function. If either of the threads exited with error,
        # then initiate shutdown which will allow the waits below to throw exception to the
        # main process.
        self._main_thread.link(self.shutdown)
        self._cleanup_thread.link(self.shutdown)

    def shutdown(self, *args, **kwargs):
        if not self._shutdown:
            self._shutdown = True

    def wait(self):
        # Wait for the worker threads to complete. If there is an exception thrown in the thread,
        # then the exception will be propagated to the main process for a proper return code.
        self._main_thread.wait() or self._cleanup_thread.wait()


def get_handler():
    return ActionExecutionSchedulingQueueHandler()
