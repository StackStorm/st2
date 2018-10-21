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
from st2common.constants import action as action_constants
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.models.db.liveaction import LiveActionDB
from st2common.services import action as action_service
from st2common.services import policies as policy_service
from st2common.persistence.liveaction import LiveAction
from st2common.util import execution_queue_db as exdb
from st2common.util import action_db as action_utils

__all__ = [
    'ExecutionQueueHandler',
    'get_handler'
]


LOG = logging.getLogger(__name__)


class ExecutionQueueHandler(object):
    def __init__(self):
        self.message_type = LiveActionDB
        self._shutdown = False

    def loop(self):
        LOG.debug('Entering scheduler loop')
        while self._shutdown is not True:
            # TODO: Make config setting
            eventlet.greenthread.sleep(0.25)
            execution = exdb.pop_next_execution()

            if execution:
                eventlet.spawn(self._handle_execution, execution)

    def _handle_execution(self, execution):
        LOG.info('Scheduling liveaction: %s', execution.liveaction.get('id'))
        try:
            liveaction_db = action_utils.get_liveaction_by_id(execution.liveaction.get('id'))
        except StackStormDBObjectNotFoundError:
            LOG.exception('Failed to find liveaction %s in the database.', execution.liveaction.id)
            raise

        # Apply policies defined for the action.
        liveaction_db = policy_service.apply_pre_run_policies(liveaction_db)

        # Exit if the status of the request is no longer runnable.
        # The status could have be changed by one of the policies.
        if liveaction_db.status not in [action_constants.LIVEACTION_STATUS_REQUESTED,
                                        action_constants.LIVEACTION_STATUS_SCHEDULED]:
            LOG.info('%s is ignoring %s (id=%s) with "%s" status after policies are applied.',
                     self.__class__.__name__, type(execution), execution.id, liveaction_db.status)
            return

        # Update liveaction status to "scheduled".
        if liveaction_db.status in [action_constants.LIVEACTION_STATUS_REQUESTED,
                                    action_constants.LIVEACTION_STATUS_DELAYED]:
            liveaction_db = action_service.update_status(
                liveaction_db, action_constants.LIVEACTION_STATUS_SCHEDULED, publish=False)

        # Publish the "scheduled" status here manually. Otherwise, there could be a
        # race condition with the update of the action_execution_db if the execution
        # of the liveaction completes first.
        LiveAction.publish_status(liveaction_db)

    def start(self):
        self._shutdown = False
        eventlet.spawn(self.loop)

    def shutdown(self):
        self._shutdown = True


def get_handler():
    return ExecutionQueueHandler()
