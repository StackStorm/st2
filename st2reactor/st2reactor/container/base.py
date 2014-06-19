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


class SensorContainer(object):
    __pool = None
    __sensors = None
    __threads = {}

    def __init__(self, sensor_instances=[]):
        self.__pool = eventlet.GreenPool(len(sensor_instances))
        self.__sensors = sensor_instances
        LOG.info('Container setup to run %d sensors.' % len(sensor_instances))

    def _run_sensor(self, sensor):
        try:
            sensor.setup()
        except Exception, e:
            LOG.error('Error calling setup on sensor: %s. Exception: %s', sensor.__class__, e)
        else:
            sensor.start()

    def _sensor_cleanup(self, sensor):
        try:
            sensor.stop()
        except Exception, e:
            LOG.error('Error cleaning up sensor: %s. Exception: %s', sensor.__class__, e)

    def shutdown(self):
        LOG.info('Container shutting down. Invoking cleanup on sensors.')
        for sensor, gt in self.__threads.iteritems():
            gt.kill()
            self._sensor_cleanup(sensor)
        LOG.info('All sensors are shut down.')

    def run(self):
        for sensor in self.__sensors:
            LOG.info('Running sensor %s' % sensor.__class__.__name__)
            gt = self.__pool.spawn(self._run_sensor, sensor)
            self.__threads[sensor] = gt
        self.__pool.waitall()

    def main(self):
        self.run()
        LOG.info('Container has no active sensors running.')
        return SUCCESS_EXIT_CODE
