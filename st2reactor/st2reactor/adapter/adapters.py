import eventlet
import logging
import random
import thread

from st2reactor.adapter import AdapterBase

LOG = logging.getLogger('st2reactor.adapter.adapters')


class FixedRunAdapter(AdapterBase):
    def __init__(self, iterations=10):
        self.__iterations = iterations

    def start(self):
        count = 0
        while self.__iterations > count:
            count += 1
            LOG.info("[{0}] iter: {1}".format(thread.get_ident(), count))
            eventlet.sleep(random.randint(1, 100)*0.01)

    def stop(self):
        pass
