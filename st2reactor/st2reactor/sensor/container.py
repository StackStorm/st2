import eventlet
import logging
from threading import Thread

# Constants
SUCCESS_EXIT_CODE = 0

eventlet.monkey_patch(
    os=True,
    select=True,
    socket=True,
    thread=True,
    time=True
)

LOG = logging.getLogger('st2reactor.sensor.container')


class SensorContainer(object):

    def __init__(self, sensor_modules=[]):
        self.__sensor_modules = sensor_modules
        self.__sensors = []

    def load(self):
        self.__sensors = [m() for m in self.__sensor_modules]
        LOG.info("Created {} sensors.".format(len(self.__sensors)))

    def run(self):
        worker_threads = []
        for m in self.__sensors:
            t = Thread(group=None, target=m.start)
            worker_threads.append((m.__class__.__name__, t))
            t.start()
        LOG.debug("No of threads {}".format(len(worker_threads)))
        for item in worker_threads:
            module_name = item[0]
            thread = item[1]
            thread.join()
            LOG.info("Thread {} running module {} has exit.".format(
                thread.ident, module_name))

    def main(self):
        self.load()
        self.run()
        return SUCCESS_EXIT_CODE
