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

import apscheduler.util as aps_utils
import dateutil.parser as date_parser
import jsonschema
import six
from apscheduler.schedulers.background import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from dateutil.tz import tzutc
from st2common.constants.pack import SYSTEM_PACK_NAME
from st2common.models.system.common import ResourceReference


INTERVAL_PARAMETERS_SCHEMA = {
    "type": "object",
    "properties": {
        "timezone": {
            "type": "string"
        },
        "unit": {
            "enum": ["weeks", "days", "hours", "minutes", "seconds"]
        },
        "delta": {
            "type": "integer"
        }
    },
    "required": [
        "unit",
        "delta"
    ],
    "additionalProperties": False
}

DATE_PARAMETERS_SCHEMA = {
    "type": "object",
    "properties": {
        "timezone": {
            "type": "string"
        },
        "date": {
            "type": "string",
            "format": "date-time"
        }
    },
    "required": [
        "date"
    ],
    "additionalProperties": False
}

CRON_PARAMETERS_SCHEMA = {
    "type": "object",
    "properties": {
        "timezone": {
            "type": "string"
        },
        "year": {
            "type": "integer"
        },
        "month": {
            "type": "integer",
            "minimum": 1,
            "maximum": 12
        },
        "day": {
            "type": "integer",
            "minimum": 1,
            "maximum": 31
        },
        "week": {
            "type": "integer",
            "minimum": 1,
            "maximum": 53
        },
        "day_of_week": {
            "type": "integer",
            "minimum": 0,
            "maximum": 6
        },
        "hour": {
            "type": "integer",
            "minimum": 0,
            "maximum": 23
        },
        "minute": {
            "type": "integer",
            "minimum": 0,
            "maximum": 59
        },
        "second": {
            "type": "integer",
            "minimum": 0,
            "maximum": 59
        }
    },
    "additionalProperties": False
}

PAYLOAD_SCHEMA = {
    "type": "object",
    "properties": {
        "executed_at": {
            "type": "string",
            "format": "date-time",
            "default": "2014-07-30 05:04:24.578325"
        },
        "schedule": {
            "type": "object",
            "default": {
                "delta": 30,
                "units": "seconds"
            }
        }
    }
}

TRIGGER_TYPES = {
    ResourceReference.to_string_reference(SYSTEM_PACK_NAME, 'st2.IntervalTimer'): {
        'name': 'st2.IntervalTimer',
        'pack': SYSTEM_PACK_NAME,
        'description': 'Triggers on specified intervals. e.g. every 30s, 1week etc.',
        'payload_schema': PAYLOAD_SCHEMA,
        'parameters_schema': INTERVAL_PARAMETERS_SCHEMA
    },
    ResourceReference.to_string_reference(SYSTEM_PACK_NAME, 'st2.DateTimer'): {
        'name': 'st2.DateTimer',
        'pack': SYSTEM_PACK_NAME,
        'description': 'Triggers exactly once when the current time matches the specified time. '
                       'e.g. timezone:UTC date:2014-12-31 23:59:59.',
        'payload_schema': PAYLOAD_SCHEMA,
        'parameters_schema': DATE_PARAMETERS_SCHEMA
    },
    ResourceReference.to_string_reference(SYSTEM_PACK_NAME, 'st2.CronTimer'): {
        'name': 'st2.CronTimer',
        'pack': SYSTEM_PACK_NAME,
        'description': 'Triggers whenever current time matches the specified time constaints like '
                       'a UNIX cron scheduler.',
        'payload_schema': PAYLOAD_SCHEMA,
        'parameters_schema': CRON_PARAMETERS_SCHEMA
    }
}


class St2TimerSensor(object):
    '''
    A timer sensor that uses APScheduler 3.0.
    '''
    def __init__(self, container_service):
        self._timezone = 'America/Los_Angeles'  # Whatever TZ local box runs in.
        self._container_service = container_service
        self._log = self._container_service.get_logger(self.__class__.__name__)
        self._scheduler = BlockingScheduler(timezone=self._timezone)
        self._jobs = {}

    def setup(self):
        pass

    def start(self):
        self._scheduler.start()

    def stop(self):
        self._scheduler.shutdown(wait=True)

    def add_trigger(self, trigger):
        self._add_job_to_scheduler(trigger)

    def update_trigger(self, trigger):
        self.remove_trigger(trigger)
        self.add_trigger(trigger)

    def remove_trigger(self, trigger):
        id = trigger['id']

        try:
            job_id = self._jobs[id]
        except KeyError:
            self._log.info('Job not found: %s', id)
            return

        self._scheduler.remove_job(job_id)

    def get_trigger_types(self):
        return [trigger_type for trigger_type in six.itervalues(TRIGGER_TYPES)]

    def _get_trigger_type(self, ref):
        pass

    def _add_job_to_scheduler(self, trigger):
        trigger_type_ref = trigger['type']
        trigger_type = TRIGGER_TYPES[trigger_type_ref]
        try:
            jsonschema.validate(trigger['parameters'],
                                trigger_type['parameters_schema'])
        except jsonschema.ValidationError as e:
            self._log.error('Exception scheduling timer: %s, %s',
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

        if hasattr(time_type, 'run_date') and datetime.now(tzutc()) > time_type.run_date:
            self._log.warning('Not scheduling expired timer: %s : %s',
                              trigger['parameters'], time_type.run_date)
        else:
            self._add_job(trigger, time_type)

    def _add_job(self, trigger, time_type, replace=True):
        try:
            job = self._scheduler.add_job(self._emit_trigger_instance,
                                          trigger=time_type,
                                          args=[trigger],
                                          replace_existing=replace)
            self._log.info('Job %s scheduled.', job.id)
            self._jobs[trigger['id']] = job.id
        except Exception as e:
            self._log.error('Exception scheduling timer: %s, %s',
                            trigger['parameters'], e, exc_info=True)

    def _emit_trigger_instance(self, trigger):
        self._log.info('Timer fired at: %s. Trigger: %s', str(datetime.utcnow()), trigger)

        payload = {
            'executed_at': str(datetime.utcnow()),
            'schedule': trigger['parameters'].get('time')
        }
        self._container_service.dispatch(trigger, payload)
