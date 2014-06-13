from datetime import timedelta
import eventlet
import sys
from threading import Thread
import time

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

LOG = logging.getLogger('st2reactor.sensor.container')


class SensorContainer(object):
    __pool = None
    __sensors = None
    __threads = {}

    def __init__(self, thread_pool_size=100, sensor_instances=[]):
        self.__pool = eventlet.GreenPool(thread_pool_size)
        self.__sensors = sensor_instances

    def _run_sensor(self, sensor):
        """
        XXX: sensor.init() needs to be called here.
        """
        sensor.start()

    def _sensor_cleanup(self, sensor):
        sensor.stop()

    def shutdown():
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
