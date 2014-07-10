from datetime import datetime
import os

from apscheduler.schedulers.background import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
# from apscheduler.executors.pool import ThreadPoolExecutor
from pytz import utc
import yaml


class St2TimerSensor(object):
    '''
    A timer sensor that uses APScheduler 3.0.
    '''
    def __init__(self, container_service):
        self._container_service = container_service
        self._log = self._container_service.get_logger(self.__class__.__name__)
        self._scheduler = BlockingScheduler()
        dirname, filename = os.path.split(os.path.abspath(__file__))
        self._config_file = os.path.join(dirname, __name__ + '.yaml')
        if not os.path.exists(self._config_file):
            raise Exception('Config file %s not found.' % self._config_file)
        with open(self._config_file) as f:
            self._config = yaml.safe_load(f)
        self._valid_time_types = set(['interval', 'cron', 'date'])
        self._valid_interval_units = set(['seconds', 'minutes', 'hours', 'days', 'weeks'])
        self._valid_cron_types = set(['year', 'month', 'day', 'week', 'day_of_week', 'hour',
                                      'minute', 'second'])
        self._jobs = {}

    def setup(self):
        if self._config is not None:
            self._add_jobs_to_scheduler(self._config)

    def start(self):
        self._scheduler.start()

    def stop(self):
        self._scheduler.shutdown(wait=True)

    def get_trigger_types(self):
        trigger_types = []
        for name, value in self._config.iteritems():
            trigger_type = {}
            trigger_type['name'] = name
            trigger_type['payload'] = {}  # For now, let's say payload is empty.
            trigger_types.append(trigger_type)
        return trigger_types

    def _add_jobs_to_scheduler(self, jobs):
        for name, value in jobs.iteritems():
            try:
                self._validate_job_spec(name, value)
            except Exception as e:
                self._log.error('Exception scheduling timer: %s', e)
                continue

            time_type = value.get('type')
            time_spec = value.get('time')

            if time_type == 'interval':
                self._add_interval_job(name, time_spec)
            elif time_type == 'cron':
                self._add_cron_job(name, time_spec)
            elif time_type == 'date':
                self._add_date_job(name, time_spec)

    def _add_interval_job(self, name, time_spec):
        interval_trigger = self._validate_interval_spec(name, time_spec)
        self._add_job(name, time_spec, interval_trigger)

    def _add_date_job(self, name, time_spec):
        date_trigger = self._validate_date_spec(name, time_spec)
        self._add_job(name, time_spec, date_trigger)

    def _add_cron_job(self, name, time_spec):
        cron_trigger = self._validate_cron_spec(name, time_spec)
        self._add_job(name, time_spec, cron_trigger)

    def _add_job(self, name, time_spec, trigger, replace=True):
        try:
            job = self._scheduler.add_job(self._emit_trigger_instance,
                                          trigger=trigger,
                                          args=[name, time_spec],
                                          replace_existing=replace)
            self._log.info('Job %s scheduled.', job.id)
            self._jobs[name] = job.id
        except Exception, e:
            self._log.error('Exception scheduling timer: %s, %s', name, e)

    def _emit_trigger_instance(self, name, time_spec):
        self._log.info('Timer: %s fired at: %s. Time spec: %s', name,
                       str(datetime.now()), time_spec)
        trigger = {}
        trigger['name'] = name
        trigger['payload'] = {
            'executed_at': str(datetime.now()),
            'schedule': time_spec
        }
        self._container_service.dispatch([trigger])

    def _validate_job_spec(self, name, value):
        time_type = value.get('type', None)
        if not time_type:
            raise Exception('No type specified for timer: %s' % name)
        if time_type not in self._valid_time_types:
            raise Exception('Invalid type specification for timer: %s, type: %s' %
                            (name, time_type))

        time_spec = value.get('time', None)
        if not time_spec:
            self._log.error('No time specified for timer: %s', name)

    def _validate_interval_spec(self, name, time_spec):
        unit = time_spec.get('unit', None)
        if not unit:
            raise Exception('Timer: %s, Error: No unit specified for time.' % name)
        if unit not in self._valid_interval_units:
            raise Exception('Timer: %s, Error: Invalid unit "%s" specified for time.' %
                (name, unit))
        value = time_spec.get('delta', None)
        if not value:
            raise Exception('Timer: %s, Error: No interval specified.' % name)
        kw = {unit: value, 'timezone': utc}
        return IntervalTrigger(**kw)

    def _validate_date_spec(self, name, time_spec):
        dat = time_spec.get('date', None)
        if not dat:
            raise Exception('Timer: %s, Error: No date specified.')
        return DateTrigger(dat)  # Raises an exception if date string isn't a valid one.

    def _validate_cron_spec(self, name, time_spec):
        cron_parts = time_spec
        cron = {}
        for key, value in cron_parts.iteritems():
            if key not in self._valid_cron_types:
                raise Exception('Invalid cron entry: %s for timer: %s' % (key, name))

            cron[key] = value

        return CronTrigger(**cron)
