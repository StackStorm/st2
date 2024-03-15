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

from st2common import log as logging
from st2common.util import date
from st2common.constants import action as action_constants
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.models.db.liveaction import LiveActionDB
from st2common.persistence.execution import ActionExecution
from st2common.transport import consumers
from st2common.transport import utils as transport_utils
from st2common.transport.queues import ACTIONSCHEDULER_REQUEST_QUEUE
from st2common.util import action_db as action_utils
from st2common.services import action as action_service
from st2common.persistence.execution_queue import ActionExecutionSchedulingQueue
from st2common.models.db.execution_queue import ActionExecutionSchedulingQueueItemDB

__all__ = ["SchedulerEntrypoint", "get_scheduler_entrypoint"]


LOG = logging.getLogger(__name__)


class SchedulerEntrypoint(consumers.MessageHandler):
    """
    SchedulerEntrypoint subscribes to the Action scheduler request queue and places new Live
    Actions into the scheduling queue collection for scheduling on action runners.
    """

    message_type = LiveActionDB

    def process(self, request):
        """
        Adds execution into execution_scheduling database for scheduling

        :param request: Action execution request.
        :type request: ``st2common.models.db.liveaction.LiveActionDB``
        """
        if request.status != action_constants.LIVEACTION_STATUS_REQUESTED:
            LOG.info(
                '%s is ignoring %s (id=%s) with "%s" status.',
                self.__class__.__name__,
                type(request),
                request.id,
                request.status,
            )
            return

        try:
            liveaction_db = action_utils.get_liveaction_by_id(str(request.id))
        except StackStormDBObjectNotFoundError:
            LOG.exception(
                "Failed to find liveaction %s in the database.", str(request.id)
            )
            raise

        query = {
            "liveaction_id": str(liveaction_db.id),
        }

        queued_requests = ActionExecutionSchedulingQueue.query(**query)

        if len(queued_requests) > 0:
            # Particular execution is already being scheduled
            return queued_requests[0]

        if liveaction_db.delay and liveaction_db.delay > 0:
            liveaction_db = action_service.update_status(
                liveaction_db, action_constants.LIVEACTION_STATUS_DELAYED, publish=False
            )

        execution_queue_item_db = self._create_execution_queue_item_db_from_liveaction(
            liveaction_db, delay=liveaction_db.delay
        )

        ActionExecutionSchedulingQueue.add_or_update(
            execution_queue_item_db, publish=False
        )

        return execution_queue_item_db

    def _create_execution_queue_item_db_from_liveaction(self, liveaction, delay=None):
        """
        Create ActionExecutionSchedulingQueueItemDB from live action.
        """
        execution = ActionExecution.get(liveaction__id=str(liveaction.id))

        execution_queue_item_db = ActionExecutionSchedulingQueueItemDB()
        execution_queue_item_db.action_execution_id = str(execution.id)
        execution_queue_item_db.liveaction_id = str(liveaction.id)
        execution_queue_item_db.original_start_timestamp = liveaction.start_timestamp
        execution_queue_item_db.scheduled_start_timestamp = (
            date.append_milliseconds_to_time(liveaction.start_timestamp, delay or 0)
        )
        execution_queue_item_db.delay = delay

        return execution_queue_item_db


def get_scheduler_entrypoint():
    with transport_utils.get_connection() as conn:
        return SchedulerEntrypoint(conn, [ACTIONSCHEDULER_REQUEST_QUEUE])
