import eventlet
import random
import thread

from reactor.stackstorm.adapter import AdapterBase


class FixedRunAdapter(AdapterBase):
    def __init__(self, iterations=10):
        self.__iterations = iterations

    def start(self):
        count = 0
        while self.__iterations > count:
            count += 1
            print "[{0}] iter: {1}".format(thread.get_ident(), count)
            eventlet.sleep(random.randint(1,100)*0.01)

    def stop(self):
        pass