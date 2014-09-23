import Queue
import threading
import time

from st2reactor.container.containerservice import ContainerService
from st2reactor.container.triggerdispatcher import TriggerDispatcher
from st2tests import EventletTestCase


class ContainerServiceTest(EventletTestCase):
    class TestDispatcher(TriggerDispatcher):
        def __init__(self):
            super(ContainerServiceTest.TestDispatcher, self).__init__()
            self.triggers_queue = Queue.Queue(maxsize=10)
            self.called_dispatch = 0
            self.lock = threading.Lock()

        def dispatch(self, trigger, payload=None):
            self.lock.acquire()
            self.called_dispatch += 1
            self.lock.release()
            self.triggers_queue.put((trigger, payload))

    def test_dispatch_pool_available(self):
        dispatcher = ContainerServiceTest.TestDispatcher()
        container_service = ContainerService(dispatch_pool_size=2,
                                             dispatcher=dispatcher)
        container_service.dispatch(True, True)
        time.sleep(0.1)  # give time for eventlet threads to dispatch.
        self.assertEqual(dispatcher.called_dispatch, 1,
                         'dispatch() should have been called only once')
        self.assertEqual(dispatcher.triggers_queue.qsize(), 1,
                         'Only one batch should have been dispatched.')
        container_service.shutdown()

    def test_dispatch_pool_full(self):
        dispatcher = ContainerServiceTest.TestDispatcher()
        container_service = ContainerService(dispatch_pool_size=2,
                                             dispatcher=dispatcher,
                                             monitor_thread_empty_q_sleep_time=0.2,
                                             monitor_thread_no_workers_sleep_time=0.1)
        for i in range(5):
            container_service.dispatch(i, i)
        time.sleep(0.3)  # give time for eventlet threads to dispatch.
        self.assertEqual(dispatcher.called_dispatch, 5,
                         'dispatch() called fewer than 5 times')
        self.assertEqual(dispatcher.triggers_queue.qsize(), 5,
                         'output queue size is not 5.')
        container_service.shutdown()
