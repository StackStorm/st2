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
from kombu import Connection

from st2common import log as logging
from st2common.constants import action as action_constants
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.models.db.liveaction import LiveActionDB
from st2common.services import action as action_service
from st2common.persistence.liveaction import LiveAction
from st2common.persistence.policy import Policy
from st2common import policies
from st2common.transport import consumers
from st2common.transport import utils as transport_utils
from st2common.util import action_db as action_utils
from st2common.transport.queues import ACTIONSCHEDULER_REQUEST_QUEUE

__all__ = [
    'ActionExecutionScheduler',
    'get_scheduler'
]


LOG = logging.getLogger(__name__)


class ActionExecutionScheduler(consumers.MessageHandler):
    message_type = LiveActionDB

    def process(self, request):
        """Schedules the LiveAction and publishes the request
        to the appropriate action runner(s).

        LiveAction in statuses other than "requested" are ignored.

        :param request: Action execution request.
        :type request: ``st2common.models.db.liveaction.LiveActionDB``
        """

        if request.status != action_constants.LIVEACTION_STATUS_REQUESTED:
            LOG.info('%s is ignoring %s (id=%s) with "%s" status.',
                     self.__class__.__name__, type(request), request.id, request.status)
            return

        try:
            liveaction_db = action_utils.get_liveaction_by_id(request.id)
        except StackStormDBObjectNotFoundError:
            LOG.exception('Failed to find liveaction %s in the database.', request.id)
            raise

        # Apply policies defined for the action.
        liveaction_db = self._apply_pre_run_policies(liveaction_db=liveaction_db)

        # Exit if the status of the request is no longer runnable.
        # The status could have be changed by one of the policies.
        if liveaction_db.status not in [action_constants.LIVEACTION_STATUS_REQUESTED,
                                        action_constants.LIVEACTION_STATUS_SCHEDULED]:
            LOG.info('%s is ignoring %s (id=%s) with "%s" status after policies are applied.',
                     self.__class__.__name__, type(request), request.id, liveaction_db.status)
            return

        # Update liveaction status to "scheduled".
        if liveaction_db.status == action_constants.LIVEACTION_STATUS_REQUESTED:
            liveaction_db = action_service.update_status(
                liveaction_db, action_constants.LIVEACTION_STATUS_SCHEDULED, publish=False)

        # Publish the "scheduled" status here manually. Otherwise, there could be a
        # race condition with the update of the action_execution_db if the execution
        # of the liveaction completes first.
        LiveAction.publish_status(liveaction_db)

    def _apply_pre_run_policies(self, liveaction_db):
        # Apply policies defined for the action.
        policy_dbs = Policy.query(resource_ref=liveaction_db.action, enabled=True)
        LOG.debug('Applying %s pre_run policies' % (len(policy_dbs)))

        for policy_db in policy_dbs:
            driver = policies.get_driver(policy_db.ref,
                                         policy_db.policy_type,
                                         **policy_db.parameters)

            try:
                LOG.debug('Applying pre_run policy "%s" (%s) for liveaction %s' %
                          (policy_db.ref, policy_db.policy_type, str(liveaction_db.id)))
                liveaction_db = driver.apply_before(liveaction_db)
            except:
                LOG.exception('An exception occurred while applying policy "%s".', policy_db.ref)

            if liveaction_db.status == action_constants.LIVEACTION_STATUS_DELAYED:
                break

        return liveaction_db


def get_scheduler():
    with Connection(transport_utils.get_messaging_urls()) as conn:
        return ActionExecutionScheduler(conn, [ACTIONSCHEDULER_REQUEST_QUEUE])
