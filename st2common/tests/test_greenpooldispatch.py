import eventlet
import mock

from st2common.util.greenpooldispatch import BufferedDispatcher
from unittest2 import TestCase


class TestGreenPoolDispatch(TestCase):

    def test_dispatch_simple(self):
        dispatcher = BufferedDispatcher(dispatch_pool_size=10)
        mock_handler = mock.MagicMock()
        expected = []
        for i in range(10):
            dispatcher.dispatch(mock_handler, i, i + 1)
            expected.append((i, i + 1))
        while mock_handler.call_count < 10:
            eventlet.sleep(0.01)
        dispatcher.shutdown()
        call_args_list = [(args[0][0], args[0][1]) for args in mock_handler.call_args_list]
        self.assertItemsEqual(expected, call_args_list)

    def test_dispatch_starved(self):
        dispatcher = BufferedDispatcher(dispatch_pool_size=2,
                                        monitor_thread_empty_q_sleep_time=0.01,
                                        monitor_thread_no_workers_sleep_time=0.01)
        mock_handler = mock.MagicMock()
        expected = []
        for i in range(10):
            dispatcher.dispatch(mock_handler, i, i + 1)
            expected.append((i, i + 1))
        while mock_handler.call_count < 10:
            eventlet.sleep(0.01)
        dispatcher.shutdown()
        call_args_list = [(args[0][0], args[0][1]) for args in mock_handler.call_args_list]
        self.assertItemsEqual(expected, call_args_list)
