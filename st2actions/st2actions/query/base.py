import abc
import eventlet
import Queue
import six
import time

from st2actions.container.service import RunnerContainerService
from st2common import log as logging
from st2common.persistence.action import ActionExecution

LOG = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class Querier(object):
    def __init__(self, threads_pool_size=10, query_interval=1, empty_q_sleep_time=5,
                 no_workers_sleep_time=1, container_service=None):
        self._query_threads_pool_size = 10
        self._query_contexts = Queue.Queue()
        self._thread_pool = eventlet.GreenPool(self._query_threads_pool_size)
        self._empty_q_sleep_time = empty_q_sleep_time
        self._no_workers_sleep_time = no_workers_sleep_time
        self._query_interval = query_interval
        if not container_service:
            container_service = RunnerContainerService()
        self.container_service = container_service

    def start(self):
        while self._query_contexts.empty():
            eventlet.greenthread.sleep(self._empty_q_sleep_time)
        while self._dispatcher_pool.free() <= 0:
            eventlet.greenthread.sleep(self._no_workers_sleep_time)
        self._fire_queries()

    def add_queries(self, query_contexts=[]):
        for query_context in query_contexts:
            self._query_contexts.put((time.time(), query_context))

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
        execution_id = query_context.execution_id
        actual_query_context = query_context.query_context

        try:
            (done, results) = self.query(execution_id, actual_query_context)
        except:
            LOG.exception('Failed querying results for action_execution_id %s.', execution_id)
            return

        try:
            self._update_action_results(execution_id, results)
        except:
            LOG.exception('Failed updating action results for action_execution_id %s',
                          execution_id)
            return

        if not done:
            self._query_contexts.put((time.time(), query_context))
            return

    def _update_action_results(self, execution_id, results):
        actionexec_db = ActionExecution.get_by_id(execution_id)
        if not actionexec_db:
            raise Exception('No DB model for action_execution_id: %s' % execution_id)
        actionexec_db.results = results
        return ActionExecution.add_or_update(actionexec_db)

    def query(self, execution_id, query_context):
        """
        This is the method individual queriers must implement.
        """
        pass


class QueryContext(object):
    def __init__(self, execution_id, query_context):
        self.execution_id = execution_id
        self.query_context = query_context
