import eventlet
import logging
import Queue

from triggerdispatcher import TriggerDispatcher


class ContainerService(object):
    _base_logger_name = 'st2reactor.sensorcontainer.sensors.'

    def __init__(self, dispatcher=None, dispatch_pool_size=50, monitor_thread_sleep_time=5):
        if dispatcher is None:
            dispatcher = TriggerDispatcher()
        self._dispatcher = dispatcher
        self._pool_limit = dispatch_pool_size
        self._dispatcher_pool = eventlet.GreenPool(dispatch_pool_size)
        self._dispatch_monitor_thread = eventlet.greenthread.spawn(self._flush_triggers)
        self._monitor_thread_sleep_time = monitor_thread_sleep_time
        self._triggers_buffer = Queue.Queue()

    def get_dispatcher(self):
        return self._dispatcher

    def dispatch(self, triggers):
        self._triggers_buffer.put(triggers, block=True, timeout=1)
        self._flush_triggers_now()

    def get_logger(self, name):
        logger = logging.getLogger(self._base_logger_name + name)
        logger.propagate = True
        return logger

    def _dispatch(self, triggers):
        self._dispatcher.dispatch(triggers)

    def _flush_triggers_now(self):
        if self._dispatcher_pool.free() <= 0:
            return
        while not self._triggers_buffer.empty() and self._dispatcher_pool.free() > 0:
            triggers = self._triggers_buffer.get_nowait()
            self._dispatcher_pool.spawn(self._dispatch, triggers)

    def _flush_triggers(self):
        while True:
            while self._triggers_buffer.empty():
                eventlet.greenthread.sleep(self._monitor_thread_sleep_time)
            while self._dispatcher_pool.free() <= 0:
                eventlet.greenthread.sleep(1)
            self._flush_triggers_now()

    def shutdown(self):
        self._dispatch_monitor_thread.kill()
