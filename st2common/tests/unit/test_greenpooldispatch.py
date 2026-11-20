# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
import mock

from st2common.util import concurrency
from st2common.util import greenpooldispatch
from st2common.util.greenpooldispatch import BufferedDispatcher
from unittest import TestCase
from six.moves import range


def wait_for(condition, timeout=5):
    waited = 0
    while not condition() and waited < timeout:
        concurrency.sleep(0.01)
        waited += 0.01
    return condition()


class TestGreenPoolDispatch(TestCase):
    def test_dispatch_simple(self):
        dispatcher = BufferedDispatcher(dispatch_pool_size=10)
        mock_handler = mock.MagicMock()
        expected = []
        for i in range(10):
            self.assertTrue(dispatcher.acquire())
            dispatcher.dispatch(mock_handler, i, i + 1)
            expected.append((i, i + 1))
        self.assertTrue(wait_for(lambda: mock_handler.call_count == 10))
        dispatcher.shutdown()
        call_args_list = [
            (args[0][0], args[0][1]) for args in mock_handler.call_args_list
        ]
        assert expected == call_args_list

    def test_dispatch_starved(self):
        dispatcher = BufferedDispatcher(dispatch_pool_size=2)
        mock_handler = mock.MagicMock()
        expected = []
        for i in range(10):
            self.assertTrue(dispatcher.acquire())
            dispatcher.dispatch(mock_handler, i, i + 1)
            expected.append((i, i + 1))
        self.assertTrue(wait_for(lambda: mock_handler.call_count == 10))
        dispatcher.shutdown()
        call_args_list = [
            (args[0][0], args[0][1]) for args in mock_handler.call_args_list
        ]
        assert expected == call_args_list

    def test_acquire_blocks_until_slot_is_free(self):
        dispatcher = BufferedDispatcher(dispatch_pool_size=2)
        finish = []

        def handler():
            while not finish:
                concurrency.sleep(0.01)

        for _ in range(2):
            self.assertTrue(dispatcher.acquire())
            dispatcher.dispatch(handler)
        self.assertEqual(dispatcher.free_count, 0)

        acquired = []
        concurrency.spawn(lambda: acquired.append(dispatcher.acquire()))
        concurrency.sleep(0.2)
        self.assertEqual(acquired, [])

        finish.append(True)
        self.assertTrue(wait_for(lambda: acquired == [True]))
        self.assertTrue(wait_for(lambda: dispatcher.free_count == 1))

    def test_slot_is_released_when_handler_raises(self):
        dispatcher = BufferedDispatcher(dispatch_pool_size=1)
        handler = mock.MagicMock(side_effect=Exception("boom"))

        self.assertTrue(dispatcher.acquire())
        dispatcher.dispatch(handler)
        self.assertTrue(wait_for(lambda: dispatcher.free_count == 1))

        self.assertTrue(dispatcher.acquire())
        dispatcher.release()
        self.assertEqual(dispatcher.free_count, 1)

    @mock.patch.object(greenpooldispatch, "SLOT_WAIT_INTERVAL_SECONDS", 0.01)
    def test_shutdown_unblocks_acquire(self):
        dispatcher = BufferedDispatcher(dispatch_pool_size=1)
        self.assertTrue(dispatcher.acquire())

        acquired = []
        concurrency.spawn(lambda: acquired.append(dispatcher.acquire()))
        concurrency.sleep(0.05)
        self.assertEqual(acquired, [])

        dispatcher.shutdown()
        self.assertTrue(wait_for(lambda: acquired == [False]))

        dispatcher.release()
        self.assertFalse(dispatcher.acquire())

    @mock.patch.object(greenpooldispatch, "SLOT_WAIT_INTERVAL_SECONDS", 0.01)
    @mock.patch.object(greenpooldispatch, "POOL_BUSY_THRESHOLD_SECONDS", 0)
    @mock.patch.object(greenpooldispatch, "LOG")
    def test_busy_pool_is_logged(self, mock_log):
        dispatcher = BufferedDispatcher(dispatch_pool_size=1, name="test")
        self.assertTrue(dispatcher.acquire())

        concurrency.spawn(dispatcher.acquire)
        self.assertTrue(wait_for(lambda: mock_log.info.called))

        dispatcher.shutdown()
