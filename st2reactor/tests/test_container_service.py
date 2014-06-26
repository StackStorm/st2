import datetime
import Queue
import threading
import time

import unittest2

from st2reactor.container.containerservice import ContainerService
from st2reactor.container.triggerdispatcher import TriggerDispatcher


def _generate_mock_trigger_instances(count=5):
    instances = []
    for i in xrange(count):
        instances.append(__make_trigger_instance(i))
    return instances


def __make_trigger_instance(id):
    mock_trigger_instance = {}
    mock_trigger_instance['id'] = 'triggerinstance-test-' + str(id)
    mock_trigger_instance['name'] = 'triggerinstance-test.name'
    mock_trigger_instance['payload'] = {}
    mock_trigger_instance['occurrence_time'] = datetime.datetime.now()
    return mock_trigger_instance


class ContainerServiceTest(unittest2.TestCase):
    class TestDispatcher(TriggerDispatcher):
        def __init__(self):
            super(ContainerServiceTest.TestDispatcher, self).__init__()
            self.triggers_queue = Queue.Queue(maxsize=10)
            self.called_dispatch = 0
            self.lock = threading.Lock()

        def dispatch(self, triggers):
            print('Test dispatch: %d' % id(self))
            self.lock.acquire()
            self.called_dispatch += 1
            print('count: %d' % self.called_dispatch)
            self.lock.release()
            print('Updating the queue.')
            self.triggers_queue.put(triggers)
            print('Queue size: %d' % self.triggers_queue.qsize())

    def test_dispatch_pool_available(self):
        dispatcher1 = ContainerServiceTest.TestDispatcher()
        container_service = ContainerService(dispatch_pool_size=2,
                                             dispatcher=dispatcher1)
        instances = _generate_mock_trigger_instances(5)
        container_service.dispatch(instances)
        time.sleep(3)  # give time for eventlet threads to dispatch.
        self.assertEquals(dispatcher1.called_dispatch, 1,
                          'dispatch() should have been called only once')
        self.assertEquals(dispatcher1.triggers_queue.qsize(), 1,
                          'Only one batch should have been dispatched.')
        print('first test done')

    def test_dispatch_pool_full(self):
        dispatcher2 = ContainerServiceTest.TestDispatcher()
        container_service = ContainerService(dispatch_pool_size=1,
                                             dispatcher=dispatcher2,
                                             monitor_thread_sleep_time=1)
        instances = []
        for i in xrange(5):
            instances.append(_generate_mock_trigger_instances(5))
        for i in xrange(5):
            container_service.dispatch(instances)
        time.sleep(6)
        self.assertEquals(dispatcher2.called_dispatch, 5,
                          'dispatch() called fewer than 5 times')
        self.assertEquals(dispatcher2.triggers_queue.qsize(), 5,
                          'output queue size is not 5.')


