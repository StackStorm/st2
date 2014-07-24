import eventlet
import sys

from st2common import log as logging

# Constants
SUCCESS_EXIT_CODE = 0

eventlet.monkey_patch(
    os=True,
    select=True,
    socket=True,
    thread=False if '--use-debugger' in sys.argv else True,
    time=True
)

LOG = logging.getLogger('st2reactor.sensorcontainer')

_sensor_container = None


class SensorContainer(object):
    def __init__(self, sensor_instances=[]):
        self._pool_size = len(sensor_instances)
        self._pool = eventlet.GreenPool(self._pool_size)
        self._sensors = sensor_instances
        self._threads = {}
        LOG.info('Container setup to run %d sensors.' % len(sensor_instances))

    def _run_sensor(self, sensor):
        try:
            sensor.setup()
        except Exception, e:
            LOG.error('Error calling setup on sensor: %s. Exception: %s',
                      sensor.__class__.__name__, e, exc_info=True)
        else:
            sensor.start()

    def _sensor_cleanup(self, sensor):
        try:
            sensor.stop()
        except Exception, e:
            LOG.error('Error cleaning up sensor: %s. Exception: %s',
                      sensor.__class__.__name__, e)

    def _spawn_sensor_in_thread(self, sensor):
        try:
            gt = self._pool.spawn(self._run_sensor, sensor)
            self._threads[sensor] = gt
            eventlet.sleep(0)
        except Exception as e:
            LOG.error('Pool doesn\'t have enough threads to run sensor: %s. Exception: %s',
                      sensor.__class__, e)

    def _run_all_sensors(self):
        for sensor in self._sensors:
            LOG.info('Running sensor %s' % sensor.__class__.__name__)
            self._spawn_sensor_in_thread(sensor)

    def add_sensor(self, sensor):
        if sensor in self._sensors:
            LOG.warning('Sensor %s already exists and running.', sensor.__class__.__name__)
            return False
        else:
            self._pool_size += 1
            self._pool.resize(self._pool_size)
            self._spawn_sensor_in_thread(sensor)
            self._sensors.append(sensor)

        return True

    def remove_sensor(self, sensor):
        if sensor not in self._sensors:
            LOG.warning('Sensor %s isn\'t running in this container.', sensor.__class__.__name__)
            return False
        else:
            self._threads[sensor].kill()
            self._sensor_cleanup(sensor)
            self._sensors.remove(sensor)
            self._pool_size -= 1
            self._pool.resize(self._pool_size)

        return True

    def get_sensor_webhook(self, name):
        sensors_hooks = (sensor.webhook for sensor in self._sensors if hasattr(sensor, 'webhook'))
        return next((hook for hook in sensors_hooks if hook.name == name), None)

    def run(self):
        self._run_all_sensors()
        self._pool.waitall()
        LOG.info('Container has no active sensors running.')
        return SUCCESS_EXIT_CODE

    def running(self):
        return len(self._sensors)

    def shutdown(self):
        LOG.info('Container shutting down. Invoking cleanup on sensors.')
        for sensor, gt in self._threads.iteritems():
            gt.kill()
            self._sensor_cleanup(sensor)
        LOG.info('All sensors are shut down.')
        self._sensors = {}
        self._threads = {}


def get_sensor_container(sensor_instances=None):
    global _sensor_container
    if not _sensor_container:
        _sensor_container = SensorContainer(sensor_instances)
    return _sensor_container

