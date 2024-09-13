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
import eventlet
import mock

from st2common.util.greenpooldispatch import BufferedDispatcher
from unittest import TestCase
from six.moves import range


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
        call_args_list = [
            (args[0][0], args[0][1]) for args in mock_handler.call_args_list
        ]
        assert expected == call_args_list

    def test_dispatch_starved(self):
        dispatcher = BufferedDispatcher(
            dispatch_pool_size=2,
            monitor_thread_empty_q_sleep_time=0.01,
            monitor_thread_no_workers_sleep_time=0.01,
        )
        mock_handler = mock.MagicMock()
        expected = []
        for i in range(10):
            dispatcher.dispatch(mock_handler, i, i + 1)
            expected.append((i, i + 1))
        while mock_handler.call_count < 10:
            eventlet.sleep(0.01)
        dispatcher.shutdown()
        call_args_list = [
            (args[0][0], args[0][1]) for args in mock_handler.call_args_list
        ]
        assert expected == call_args_list
