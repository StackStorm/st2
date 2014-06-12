import eventlet
import sys
from threading import Thread

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
    __sensors = None

    def __init__(self, sensor_instances=[]):
        self.__sensors = sensor_instances

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
        self.run()
        return SUCCESS_EXIT_CODE
