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

from oslo_config import cfg
from apscheduler.schedulers.background import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
import apscheduler.util as aps_utils

from st2common import log as logging
from st2common.constants import action as action_constants
from st2common.services import coordination
from st2common.util import date as date_utils
from st2common.services import action as action_service
from st2common.persistence.liveaction import LiveAction

__all__ = [
    'get_rescheduler',
    'recover_delayed_executions'
]

LOG = logging.getLogger(__name__)


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
                  next_run_time=date_utils.get_datetime_utc_now(),
                  replace_existing=True)

    return timer


def recover_delayed_executions():
    coordinator = coordination.get_coordinator()
    dt_now = date_utils.get_datetime_utc_now()
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
