from apscheduler.schedulers.background import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
import apscheduler.util as aps_utils
from datetime import datetime
import dateutil.parser as date_parser
from dateutil.tz import tzutc
import jsonschema


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
    'st2.IntervalTimer': {
        'payload_schema': PAYLOAD_SCHEMA,
        'parameters_schema': INTERVAL_PARAMETERS_SCHEMA
    },
    'st2.DateTimer': {
        'payload_schema': PAYLOAD_SCHEMA,
        'parameters_schema': DATE_PARAMETERS_SCHEMA
    },
    'st2.CronTimer': {
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
        return [dict(name=key, **value) for key, value in TRIGGER_TYPES.items()]

    def _add_job_to_scheduler(self, trigger):
        name = trigger['type']['name']
        try:
            jsonschema.validate(trigger['parameters'], TRIGGER_TYPES[name]['parameters_schema'])
        except jsonschema.ValidationError as e:
            self._log.error('Exception scheduling timer: %s, %s',
                            trigger['parameters'], e, exc_info=True)
            raise  # Or should we just return?

        time_spec = trigger['parameters']
        time_zone = aps_utils.astimezone(trigger['parameters'].get('timezone'))

        time_type = None

        if name == 'st2.IntervalTimer':
            unit = time_spec.get('unit', None)
            value = time_spec.get('delta', None)
            time_type = IntervalTrigger(**{unit: value, 'timezone': time_zone})
        elif name == 'st2.DateTimer':
            # Raises an exception if date string isn't a valid one.
            dat = date_parser.parse(time_spec.get('date', None))
            time_type = DateTrigger(dat, timezone=time_zone)
        elif name == 'st2.CronTimer':
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
            self._jobs[trigger['_id']] = job.id
        except Exception, e:
            self._log.error('Exception scheduling timer: %s, %s',
                            trigger['parameters'], e, exc_info=True)

    def _emit_trigger_instance(self, trigger):
        self._log.info('Timer fired at: %s. Trigger: %s', str(datetime.now()), trigger)

        payload = {
            'executed_at': str(datetime.now()),
            'schedule': trigger['parameters'].get('time')
        }
        self._container_service.dispatch(trigger, payload)
