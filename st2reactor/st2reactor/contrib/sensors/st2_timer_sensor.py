from datetime import datetime
import os

from apscheduler.schedulers.background import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
import apscheduler.util as aps_utils
import dateutil.parser as date_parser
from dateutil.tz import tzutc
import jsonschema
import yaml


PARAMETERS_SCHEMA = {
    "oneOf": [{
        "type": "object",
        "properties": {
            "type": {
                "enum": ["cron"]
            },
            "timezone": {
                "type": "string"
            },
            "time": {
                "type": "object",
                "properties": {
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
                }
            }
        },
        "required": [
            "type",
            "time"
        ],
        "additionalProperties": False
    }, {
        "type": "object",
        "properties": {
            "type": {
                "enum": ["interval"]
            },
            "timezone": {
                "type": "string"
            },
            "time": {
                "type": "object",
                "properties": {
                    "units": {
                        "enum": ["weeks", "days", "hours", "minutes", "seconds"]
                    },
                    "delta": {
                        "type": "integer"
                    }
                }
            }
        },
        "required": [
            "type",
            "time"
        ],
        "additionalProperties": False
    }, {
        "type": "object",
        "properties": {
            "type": {
                "enum": ["date"]
            },
            "timezone": {
                "type": "string"
            },
            "time": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "format": "date-time"
                    }
                }
            }
        },
        "required": [
            "type",
            "time"
        ],
        "additionalProperties": False
    }]
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
        pass

    def remove_trigger(self, trigger):
        id = trigger['_id']

        try:
            job_id = self._jobs[id]
        except KeyError:
            self._log.info('Job not found: %s', id)
            return

        self._scheduler.remove_job(job_id)

    def get_trigger_types(self):
        return [{
            'name': 'st2.timer',
            'payload_schema': PAYLOAD_SCHEMA,
            'parameters_schema': PARAMETERS_SCHEMA
        }]

    def _add_job_to_scheduler(self, trigger):
        try:
            jsonschema.validate(trigger['parameters'], PARAMETERS_SCHEMA)
        except Exception as e:
            self._log.error('Exception scheduling timer: %s, %s',
                            trigger['parameters'], e, exc_info=True)

        time_type = trigger['parameters'].get('type')
        # time_spec = parameters.get('time')
        # time_zone = aps_utils.astimezone(parameters.get('timezone'))

        if time_type == 'interval':
            self._add_interval_job(trigger)
        elif time_type == 'cron':
            self._add_cron_job(trigger)
        elif time_type == 'date':
            self._add_date_job(trigger)

    def _add_interval_job(self, trigger):
        time_spec = trigger['parameters'].get('time')
        time_zone = aps_utils.astimezone(trigger['parameters'].get('timezone'))

        unit = time_spec.get('unit', None)
        value = time_spec.get('delta', None)

        interval_trigger = IntervalTrigger(**{unit: value, 'timezone': time_zone})
        self._add_job(trigger, interval_trigger)

    def _add_date_job(self, trigger):
        time_spec = trigger['parameters'].get('time')
        time_zone = aps_utils.astimezone(trigger['parameters'].get('timezone'))

        dat = date_parser.parse(time_spec.get('date', None))  # Raises an exception if date string isn't a valid one.
        date_trigger = DateTrigger(dat, timezone=time_zone)

        if datetime.now(tzutc()) < date_trigger.run_date:
            self._add_job(trigger, date_trigger)
        else:
            self._log.warning('Not scheduling expired timer: %s : %s', trigger['parameters'], date_trigger.run_date)

    def _add_cron_job(self, trigger):
        time_spec = trigger['parameters'].get('time')
        time_zone = aps_utils.astimezone(trigger['parameters'].get('timezone'))

        cron = time_spec
        cron['timezone'] = time_zone

        cron_trigger = CronTrigger(**cron)
        self._add_job(trigger, cron_trigger)

    def _add_job(self, trigger, type, replace=True):
        def hashify(d):
            return frozenset(
                (k, hashify(v)) if type(v) is dict else (k, v) for (k, v) in d.iteritems()
            )

        try:
            job = self._scheduler.add_job(self._emit_trigger_instance,
                                          trigger=type,
                                          args=[trigger],
                                          replace_existing=replace)
            self._log.info('Job %s scheduled.', job.id)
            self._jobs[trigger['_id']] = job.id
        except Exception, e:
            self._log.error('Exception scheduling timer: %s, %s', trigger['parameters'], e, exc_info=True)

    def _emit_trigger_instance(self, trigger):
        self._log.info('Timer fired at: %s. Trigger: %s', str(datetime.now()), trigger)

        payload = {
            'executed_at': str(datetime.now()),
            'schedule': trigger['parameters'].get('time')
        }
        self._container_service.dispatch(trigger, payload)
