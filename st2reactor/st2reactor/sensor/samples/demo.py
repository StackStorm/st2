import eventlet
import random
import thread

from st2common import log as logging


LOG = logging.getLogger('st2reactor.sensor.sensors')


class FixedRunSensor(object):
    __iterations = 10

    def start(self):
        count = 0
        while self.__iterations > count:
            count += 1
            LOG.info("[{0}] iter: {1}".format(thread.get_ident(), count))
            eventlet.sleep(random.randint(1, 100) * 0.01)

    def stop(self):
        pass

    def get_trigger_types(self):
        return [
            {'name': 'st2.dummy.t1', 'description': 'some desc 1', 'payload_info': ['a', 'b']}
        ]

from st2reactor.container.utils import dispatch_triggers


class DummyTriggerGeneratorSensor(object):
    __iterations = 10

    def start(self):
        self.__dispatch_trigger_instances()

    def stop(self):
        self.__iterations = -1

    def get_trigger_types(self):
        return [
            {'name': 'st2.dummy.t2', 'description': 'some desc 2', 'payload_info': ['c', 'd']},
            {'name': 'st2.dummy.t3', 'description': 'some desc 3', 'payload_info': ['e', 'f']}
        ]

    def __dispatch_trigger_instances(self):
        count = 0
        while self.__iterations > count:
            count += 1
            LOG.info("[{0}] of sensor {1} iter: {2}".format(
                thread.get_ident(), self.__class__.__name__, count))
            dispatch_triggers([
                {'name': 'st2.dummy.t1', 'payload': {'t1_p': 't1_p_v'}},
                {'name': 'st2.dummy.t2', 'payload': {'t2_p': 't2_p_v'}}])
            eventlet.sleep(1)

