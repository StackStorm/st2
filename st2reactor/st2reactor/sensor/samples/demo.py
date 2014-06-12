import eventlet
import logging
import random
import thread

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


from st2reactor.container.utils import add_trigger_types, \
    dispatch_triggers


class DummyTriggerGeneratorSensor(object):
    __iterations = 10

    def start(self):
        DummyTriggerGeneratorSensor.__add_triggers()
        self.__dispatch_trigger_instances()

    def stop(self):
        self.__iterations = -1

    def __dispatch_trigger_instances(self):
        count = 0
        while self.__iterations > count:
            count += 1
            LOG.info("[{0}] of sensor {1} iter: {2}".format(
                thread.get_ident(), self.__class__.__name__, count))
            dispatch_triggers([
                {'name': 'st2.dummy.t1', 'payload': {'t1_p': 't1_p_v'}},
                {'name': 'st2.dummy.t2', 'payload': {'t2_p': 't2_p_v'}},
                {'name': 'st2.dummy.t3', 'payload': {'t3_p': 't3_p_v'}}])
            eventlet.sleep(1)

    @staticmethod
    def __add_triggers():
        add_trigger_types([
            {'name': 'st2.dummy.t1', 'description': 'some desc 1', 'payload_info': ['t1_p']},
            {'name': 'st2.dummy.t2', 'description': 'some desc 2', 'payload_info': ['t2_p']},
            {'name': 'st2.dummy.t3', 'description': 'some desc 3', 'payload_info': ['t3_p']}
        ])
