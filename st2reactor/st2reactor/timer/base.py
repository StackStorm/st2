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

import uuid

from apscheduler.schedulers.background import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
import apscheduler.util as aps_utils
import dateutil.parser as date_parser
import jsonschema

from st2common import log as logging
from st2common.constants.triggers import TIMER_TRIGGER_TYPES
from st2common.models.api.trace import TraceContext
from st2common.models.api.trigger import TriggerAPI
import st2common.services.triggers as trigger_services
from st2common.services.triggerwatcher import TriggerWatcher
from st2common.transport.reactor import TriggerDispatcher
from st2common.util import date as date_utils
from st2common.util import schema as util_schema

LOG = logging.getLogger(__name__)


class St2Timer(object):
    """
    A timer interface that uses APScheduler 3.0.
    """
    def __init__(self, local_timezone=None):
        self._timezone = local_timezone
        self._scheduler = BlockingScheduler(timezone=self._timezone)
        self._jobs = {}
        self._trigger_types = TIMER_TRIGGER_TYPES.keys()
        self._trigger_watcher = TriggerWatcher(create_handler=self._handle_create_trigger,
                                               update_handler=self._handle_update_trigger,
                                               delete_handler=self._handle_delete_trigger,
                                               trigger_types=self._trigger_types,
                                               queue_suffix=self.__class__.__name__,
                                               exclusive=True)
        self._trigger_dispatcher = TriggerDispatcher(LOG)

    def start(self):
        self._register_timer_trigger_types()
        self._trigger_watcher.start()
        self._scheduler.start()

    def cleanup(self):
        self._scheduler.shutdown(wait=True)

    def add_trigger(self, trigger):
        self._add_job_to_scheduler(trigger)

    def update_trigger(self, trigger):
        self.remove_trigger(trigger)
        self.add_trigger(trigger)

    def remove_trigger(self, trigger):
        trigger_id = trigger['id']

        try:
            job_id = self._jobs[trigger_id]
        except KeyError:
            LOG.info('Job not found: %s', trigger_id)
            return

        self._scheduler.remove_job(job_id)
        del self._jobs[trigger_id]

    def _add_job_to_scheduler(self, trigger):
        trigger_type_ref = trigger['type']
        trigger_type = TIMER_TRIGGER_TYPES[trigger_type_ref]
        try:
            util_schema.validate(instance=trigger['parameters'],
                                 schema=trigger_type['parameters_schema'],
                                 cls=util_schema.CustomValidator,
                                 use_default=True,
                                 allow_default_none=True)
        except jsonschema.ValidationError as e:
            LOG.error('Exception scheduling timer: %s, %s',
                      trigger['parameters'], e, exc_info=True)
            raise  # Or should we just return?

        time_spec = trigger['parameters']
        time_zone = aps_utils.astimezone(trigger['parameters'].get('timezone'))

        time_type = None

        if trigger_type['name'] == 'st2.IntervalTimer':
            unit = time_spec.get('unit', None)
            value = time_spec.get('delta', None)
            time_type = IntervalTrigger(**{unit: value, 'timezone': time_zone})
        elif trigger_type['name'] == 'st2.DateTimer':
            # Raises an exception if date string isn't a valid one.
            dat = date_parser.parse(time_spec.get('date', None))
            time_type = DateTrigger(dat, timezone=time_zone)
        elif trigger_type['name'] == 'st2.CronTimer':
            cron = time_spec.copy()
            cron['timezone'] = time_zone

            time_type = CronTrigger(**cron)

        utc_now = date_utils.get_datetime_utc_now()
        if hasattr(time_type, 'run_date') and utc_now > time_type.run_date:
            LOG.warning('Not scheduling expired timer: %s : %s',
                        trigger['parameters'], time_type.run_date)
        else:
            self._add_job(trigger, time_type)
        return time_type

    def _add_job(self, trigger, time_type, replace=True):
        try:
            job = self._scheduler.add_job(self._emit_trigger_instance,
                                          trigger=time_type,
                                          args=[trigger],
                                          replace_existing=replace)
            LOG.info('Job %s scheduled.', job.id)
            self._jobs[trigger['id']] = job.id
        except Exception as e:
            LOG.error('Exception scheduling timer: %s, %s',
                      trigger['parameters'], e, exc_info=True)

    def _emit_trigger_instance(self, trigger):
        utc_now = date_utils.get_datetime_utc_now()
        # debug logging is reasonable for this one. A high resolution timer will end up
        # trashing standard logs.
        LOG.debug('Timer fired at: %s. Trigger: %s', str(utc_now), trigger)

        payload = {
            'executed_at': str(utc_now),
            'schedule': trigger['parameters'].get('time')
        }

        trace_context = TraceContext(trace_tag='%s-%s' % (self._get_trigger_type_name(trigger),
                                                          trigger.get('name', uuid.uuid4().hex)))
        self._trigger_dispatcher.dispatch(trigger, payload, trace_context=trace_context)

    def _get_trigger_type_name(self, trigger):
        trigger_type_ref = trigger['type']
        trigger_type = TIMER_TRIGGER_TYPES[trigger_type_ref]
        return trigger_type['name']

    def _register_timer_trigger_types(self):
        return trigger_services.add_trigger_models(TIMER_TRIGGER_TYPES.values())

    ##############################################
    # Event handler methods for the trigger events
    ##############################################

    def _handle_create_trigger(self, trigger):
        LOG.debug('Calling "add_trigger" method (trigger.type=%s)' % (trigger.type))
        trigger = self._sanitize_trigger(trigger=trigger)
        self.add_trigger(trigger=trigger)

    def _handle_update_trigger(self, trigger):
        LOG.debug('Calling "update_trigger" method (trigger.type=%s)' % (trigger.type))
        trigger = self._sanitize_trigger(trigger=trigger)
        self.update_trigger(trigger=trigger)

    def _handle_delete_trigger(self, trigger):
        LOG.debug('Calling "remove_trigger" method (trigger.type=%s)' % (trigger.type))
        trigger = self._sanitize_trigger(trigger=trigger)
        self.remove_trigger(trigger=trigger)

    def _sanitize_trigger(self, trigger):
        sanitized = TriggerAPI.from_model(trigger).to_dict()
        return sanitized
