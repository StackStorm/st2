from datetime import datetime
import os

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import eventlet
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
        self._scheduler = BackgroundScheduler()
        dirname, filename = os.path.split(os.path.abspath(__file__))
        self._config_file = os.path.join(dirname, __name__ + '.yaml')
        if not os.path.exists(self._config_file):
            raise Exception('Config file %s not found.' % self._config_file)
        self._config = None
        self._valid_time_types = set(['interval', 'cron'])
        self._valid_interval_units = set(['seconds', 'minutes', 'hours', 'days', 'weeks'])

    def setup(self):
        self._scheduler.start()
        with open(self._config_file) as f:
            self._config = yaml.safe_load(f)
            schedule = self._config
            if schedule is not None:
                self._add_jobs_to_scheduler(schedule)

    def start(self):
        while True:
            eventlet.sleep(30)

    def stop(self):
        self._scheduler.shutdown(wait=True)

    def get_trigger_types(self):
        return []

    def _add_jobs_to_scheduler(self, jobs):
        for name, value in jobs.iteritems():
            time_type = value.get('type', None)

            if not time_type:
                self._log.error('No type specified for timer: %s', name)
            if time_type not in self._valid_time_types:
                self._log.error('Invalid type specification for timer: %s, type: %s',
                                name, time_type)

            time_spec = value.get('time', None)

            if not time_spec:
                self._log.error('No time specified for timer: %s', name)

            if time_type == 'interval':
                self._add_interval_job(name, time_spec)
            elif time_type == 'cron':
                self._add_cron_job(name, time_spec)

    def _add_interval_job(self, name, time_spec):
        unit = time_spec.get('unit', None)
        if not unit:
            raise Exception('Timer: %s, Error: No unit specified for time.', name)
        if unit not in self._valid_interval_units:
            raise Exception('Timer: %s, Error: Invalid unit "%s" specified for time.', name, unit)
        value = time_spec.get('delta', None)
        if not value:
            raise Exception('Timer: %s, Error: No interval specified.', name)
        kw = {unit: value, 'timezone': utc}
        interval_trigger = IntervalTrigger(**kw)
        job = self._scheduler.add_job(self._emit_trigger_instance, trigger=interval_trigger,
                                      args=[name, time_spec])
        self._log.info('Job %s scheduled.' % job)

    def _add_cron_job(self, name, time_spec):
        pass

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
