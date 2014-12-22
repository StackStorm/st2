import abc
import eventlet
import Queue
import six
import time

from st2actions.container.service import RunnerContainerService


@six.add_metaclass(abc.ABCMeta)
class Querier(object):
    def __init__(self, threads_pool_size=10, query_interval=1, empty_q_sleep_time=5,
                 no_workers_sleep_time=1):
        self._query_threads_pool_size = 10
        self._query_contexts = Queue.Queue()
        self._thread_pool = eventlet.GreenPool(self._query_threads_pool_size)
        self._empty_q_sleep_time = empty_q_sleep_time
        self._no_workers_sleep_time = no_workers_sleep_time
        self._query_interval = query_interval
        self._container_service = RunnerContainerService()

    def start(self):
        while self._query_contexts.empty():
            eventlet.greenthread.sleep(self._empty_q_sleep_time)
        while self._dispatcher_pool.free() <= 0:
            eventlet.greenthread.sleep(self._no_workers_sleep_time)
        self._fire_queries()

    def add_queries(self, query_contexts=[]):
        for context in query_contexts:
            self._query_contexts.put((time.time(), context))

    def _fire_queries(self):
        if self._dispatcher_pool.free() <= 0:
            return
        while not self._query_contexts.empty() and self._dispatcher_pool.free() > 0:
            (last_query_time, query_context) = self._query_contexts.get_nowait()
            if time.time() - last_query_time < self._query_interval:
                self._query_contexts.put((last_query_time, query_context))
                continue
            self._dispatcher_pool.spawn(self._query_and_save_results, query_context)

    def _query_and_save_results(self, query_context):
        results = self.query(query_context)
        if not results:
            self._query_contexts.put((time.time(), query_context))
            return
        # XXX: Should actually update actionexec db
        self._container_service.report_result(results)

    def query(self, query_context):
        """
        This is the method individual queriers must implement.
        """
        pass
