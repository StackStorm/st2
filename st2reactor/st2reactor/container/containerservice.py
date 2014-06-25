import eventlet
import logging
import Queue

from triggerdispatcher import TriggerDispatcher


class ContainerService(object):
    __dispatcher = None
    __dispatcher_pool = None
    __pool_limit = None
    __triggers_buffer = Queue.Queue()
    __dispatch_monitor_thread = None
    __base_logger_name = 'st2reactor.sensorcontainer.sensors.'

    def __init__(self, dispatcher=TriggerDispatcher(), dispatch_pool_size=50):
        self.__dispatcher = dispatcher
        self.__pool_limit = dispatch_pool_size
        self.__dispatcher_pool = eventlet.GreenPool(dispatch_pool_size)
        self.__dispatch_monitor_thread = eventlet.greenthread.spawn(self._flush_triggers)

    def get_dispatcher(self):
        return self.__dispatcher

    def dispatch(self, triggers):
        if self.__dispatcher_pool.free() <= 0:
            self.__triggers_buffer.put(triggers, block=True, timeout=1)
            return
        self.__dispatcher_pool.spawn(self._dispatch, triggers)

    def get_logger(self, name):
        logger = logging.getLogger(self.__base_logger_name + name)
        logger.propagate = True
        return logger

    def _dispatch(self, triggers):
        self.__dispatcher.dispatch(triggers)

    def _flush_triggers(self):
        while True:
            while self.__triggers_buffer.empty():
                eventlet.greenthread.sleep(5)
            while self.__dispatcher_pool.free() <= 0:
                eventlet.greenthread.sleep(1)
            while not self.__triggers_buffer.empty() and self.__dispatcher_pool.free() > 0:
                triggers = self.__triggers_buffer.get_nowait()
                self.dispatch(triggers)


