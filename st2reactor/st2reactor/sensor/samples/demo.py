import eventlet
import logging
import random
import thread


class FixedRunSensor(object):
    __container_service = None
    __iterations = 10
    __log = None

    def __init__(self, container_service):
        self.__container_service = container_service

    def setup(self):
        self.__log = self.__container_service.get_logger(self.__class__.__name__)
        hdlr = logging.FileHandler('/tmp/demosensor.log')
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        hdlr.setFormatter(formatter)
        self.__log.addHandler(hdlr)
        pass

    def start(self):
        count = 0
        while self.__iterations > count:
            count += 1
            self.__log.info("[{0}] iter: {1}".format(thread.get_ident(), count))
            eventlet.sleep(random.randint(1, 100) * 0.01)

    def stop(self):
        pass

    def get_trigger_types(self):
        return [
            {'name': 'st2.dummy.t1', 'description': 'some desc 1', 'payload_info': ['a', 'b']}
        ]


class DummyTriggerGeneratorSensor(object):
    __container_service = None
    __iterations = 10
    __log = None

    def __init__(self, container_service):
        self.__container_service = container_service

    def setup(self):
        self.__log = self.__container_service.get_logger(self.__class__.__name__)
        pass

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
            self.__log.info("[{0}] of sensor {1} iter: {2}".format(
                thread.get_ident(), self.__class__.__name__, count))
            self.__container_service.dispatch([
                {'name': 'st2.dummy.t1', 'payload': {'t1_p': 't1_p_v'}},
                {'name': 'st2.dummy.t2', 'payload': {'t2_p': 't2_p_v'}}])
            eventlet.sleep(1)
