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
from oslo.config import cfg

from st2common import log as logging
from st2common.constants import action as action_constants
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.models.db.liveaction import LiveActionDB
from st2common.services import executions
from st2common.persistence.liveaction import LiveAction
from st2common.persistence.policy import Policy
from st2common import policies
from st2common.transport import consumers, liveaction
from st2common.util import action_db as action_utils


LOG = logging.getLogger(__name__)

ACTIONRUNNER_REQUEST_Q = liveaction.get_status_management_queue(
    'st2.actionrunner.req', routing_key=action_constants.LIVEACTION_STATUS_REQUESTED)


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
        for policy_db in Policy.query(resource_ref=liveaction_db.action):
            driver = policies.get_driver(policy_db.ref,
                                         policy_db.policy_type,
                                         **policy_db.parameters)

            try:
                liveaction_db = driver.apply(liveaction_db)
            except:
                LOG.exception('An exception occurred while applying policy "%s".', policy_db.ref)

            if liveaction_db.status == action_constants.LIVEACTION_STATUS_DELAYED:
                break

        # Exit if the status of the request is no longer runnable.
        # The status could have be changed by one of the policies.
        if liveaction_db.status not in [action_constants.LIVEACTION_STATUS_REQUESTED,
                                        action_constants.LIVEACTION_STATUS_SCHEDULED]:
            LOG.info('%s is ignoring %s (id=%s) with "%s" status after policies are applied.',
                     self.__class__.__name__, type(request), request.id, liveaction_db.status)
            return

        # Update liveaction status to "scheduled"
        if liveaction_db.status == action_constants.LIVEACTION_STATUS_REQUESTED:
            liveaction_db = action_utils.update_liveaction_status(
                status=action_constants.LIVEACTION_STATUS_SCHEDULED,
                liveaction_id=liveaction_db.id,
                publish=False)

            action_execution_db = executions.update_execution(liveaction_db)

            extra = {'action_execution_db': action_execution_db, 'liveaction_db': liveaction_db}
            LOG.audit('Scheduled action execution.', extra=extra)

            # the extra field will not be shown in non-audit logs so temporarily log at info.
            LOG.info('Scheduled {~}action_execution: %s / {~}live_action: %s with "%s" status.',
                     action_execution_db.id, liveaction_db.id, request.status)

        # Publish the "scheduled" status here manually. Otherwise, there could be a
        # race condition with the update of the action_execution_db if the execution
        # of the liveaction completes first.
        LiveAction.publish_status(liveaction_db)


def get_scheduler():
    with Connection(cfg.CONF.messaging.url) as conn:
        return ActionExecutionScheduler(conn, [ACTIONRUNNER_REQUEST_Q])
