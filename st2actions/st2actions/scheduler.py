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

import datetime

from apscheduler.schedulers.background import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
import apscheduler.util as aps_utils
from kombu import Connection
from oslo.config import cfg

from st2common import log as logging
from st2common.constants import action as action_constants
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.models.db.liveaction import LiveActionDB
from st2common.services import action as action_service
from st2common.services import coordination
from st2common.persistence.liveaction import LiveAction
from st2common.persistence.policy import Policy
from st2common import policies
from st2common.transport import consumers, liveaction
from st2common.util import action_db as action_utils
from st2common.util import isotime


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
                liveaction_db = driver.apply_before(liveaction_db)
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

        # Update liveaction status to "scheduled".
        if liveaction_db.status == action_constants.LIVEACTION_STATUS_REQUESTED:
            liveaction_db = action_service.update_status(
                liveaction_db, action_constants.LIVEACTION_STATUS_SCHEDULED, publish=False)

        # Publish the "scheduled" status here manually. Otherwise, there could be a
        # race condition with the update of the action_execution_db if the execution
        # of the liveaction completes first.
        LiveAction.publish_status(liveaction_db)


def get_scheduler():
    with Connection(cfg.CONF.messaging.url) as conn:
        return ActionExecutionScheduler(conn, [ACTIONRUNNER_REQUEST_Q])


def recover_delayed_executions():
    coordinator = coordination.get_coordinator()
    dt_now = isotime.add_utc_tz(datetime.datetime.utcnow())
    dt_delta = datetime.timedelta(seconds=cfg.CONF.scheduler.delayed_execution_recovery)
    dt_timeout = dt_now - dt_delta

    with coordinator.get_lock('st2-rescheduling-delayed-executions'):
        liveactions = LiveAction.query(status=action_constants.LIVEACTION_STATUS_DELAYED,
                                       start_timestamp__lte=dt_timeout,
                                       order_by=['start_timestamp'])

        if not liveactions:
            return

        LOG.info('There are %d liveactions that have been delayed for longer than %d seconds.',
                 len(liveactions), cfg.CONF.scheduler.delayed_execution_recovery)

        # Update status to requested and publish status for each liveactions.
        rescheduled = 0
        for instance in liveactions:
            try:
                action_service.update_status(instance,
                                             action_constants.LIVEACTION_STATUS_REQUESTED,
                                             publish=True)
                rescheduled += 1
            except:
                LOG.exception('Unable to reschedule liveaction. <LiveAction.id=%s>', instance.id)

        LOG.info('Rescheduled %d out of %d delayed liveactions.', len(liveactions), rescheduled)


def get_rescheduler():
    timer = BlockingScheduler()

    time_spec = {
        'seconds': cfg.CONF.scheduler.rescheduling_interval,
        'timezone': aps_utils.astimezone('UTC')
    }

    timer.add_job(recover_delayed_executions,
                  trigger=IntervalTrigger(**time_spec),
                  max_instances=1,
                  misfire_grace_time=60,
                  next_run_time=datetime.datetime.utcnow(),
                  replace_existing=True)

    return timer
