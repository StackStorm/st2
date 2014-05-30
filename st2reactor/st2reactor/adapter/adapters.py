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

import eventlet
from st2reactor.adapter.containerservice import add_trigger_types, \
    dispatch_triggers


class DummyTriggerGeneratorAdapter(AdapterBase):
    def __init__(self, iterations=10):
        self.__iterations = iterations

    def start(self):
        DummyTriggerGeneratorAdapter.__add_triggers()
        self.__dispatch_trigger_instances()

    def stop(self):
        self.__iterations = -1

    def __dispatch_trigger_instances(self):
        count = 0
        while self.__iterations > count:
            count += 1
            LOG.info("[{0}] of adapter {1} iter: {2}".format(
                thread.get_ident(), self.__class__.__name__, count))
            dispatch_triggers([
                {'name': 'st2.dummy.t1', 'payload': {'t1_p': 't1_p_v'}},
                {'name': 'st2.dummy.t2', 'payload': {'t2_p': 't2_p_v'}},
                {'name': 'st2.dummy.t3', 'payload': {'t3_p': 't3_p_v'}}])
            eventlet.sleep(1)

    @staticmethod
    def __add_triggers():
        add_trigger_types([
            {'name': 'st2.dummy.t1'},
            {'name': 'st2.dummy.t2'},
            {'name': 'st2.dummy.t3'}
        ])
