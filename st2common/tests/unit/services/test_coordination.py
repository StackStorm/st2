# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, print_function

from unittest2 import TestCase
from mock import patch, MagicMock
from oslo_config import cfg

import st2tests.config as tests_config
from st2common.services import coordination

MOCK_NOOPLOCK = MagicMock(spec=coordination.locking.Lock)
MOCK_NOOPLOCK().acquire.return_value = True
MOCK_NOOPLOCK().release.return_value = True
MOCK_NOOPLOCK().heartbeat.return_value = True


class CoordinationTest(TestCase):
    @classmethod
    def setUpClass(cls):
        tests_config.parse_args()
        tests_config.CONF.set_override(name='url', override=None, group='coordination')

    @patch('st2common.services.coordination.NoOpLock', MOCK_NOOPLOCK)
    def test_lock_decorator(self):
        MOCK_NOOPLOCK.reset_mock()
        lock_name = 'fakelock'

        @coordination.lock(lock_name)
        def _decorated():
            pass

        _decorated()

        MOCK_NOOPLOCK().acquire.assert_called_once()
        MOCK_NOOPLOCK().release.assert_called_once()

    @patch('st2common.services.coordination.NoOpLock', MOCK_NOOPLOCK)
    def test_lock_context_manager(self):
        MOCK_NOOPLOCK.reset_mock()
        lock_name = 'fakelock'

        with coordination.lock(lock_name):
            pass

        MOCK_NOOPLOCK().acquire.assert_called_once()
        MOCK_NOOPLOCK().release.assert_called_once()


    @patch('st2common.services.coordination.NoOpLock', MOCK_NOOPLOCK)
    def test_lock_context_manager_fail(self):
        MOCK_NOOPLOCK.reset_mock()
        MOCK_NOOPLOCK().acquire.return_value = False
        lock_name = 'fakelock'

        with self.assertRaises(coordination.LockAcquireError):
            with coordination.lock(lock_name, timeout=2):
                pass

        self.assertEquals(MOCK_NOOPLOCK().acquire.call_count, 2)

        MOCK_NOOPLOCK().acquire.return_value = True

    @patch('st2common.services.coordination.NoOpLock', MOCK_NOOPLOCK)
    def test_lock_decorator_fail(self):
        MOCK_NOOPLOCK.reset_mock()
        MOCK_NOOPLOCK().acquire.return_value = False
        lock_name = 'fakelock'

        @coordination.lock(lock_name, timeout=2)
        def _decorated():
            pass

        with self.assertRaises(coordination.LockAcquireError):
            _decorated()

        self.assertEquals(MOCK_NOOPLOCK().acquire.call_count, 2)

        MOCK_NOOPLOCK().acquire.return_value = True

    @patch('st2common.services.coordination.NoOpLock', MOCK_NOOPLOCK)
    def test_lock_context_manager_eventually_succeed(self):
        MOCK_NOOPLOCK.reset_mock()
        MOCK_NOOPLOCK().acquire.side_effect = [False, False, True]
        lock_name = 'fakelock'

        with coordination.lock(lock_name):
            pass

        self.assertEquals(MOCK_NOOPLOCK().acquire.call_count, 3)
        MOCK_NOOPLOCK().release.assert_called_once()

        MOCK_NOOPLOCK().acquire.return_value = True
        MOCK_NOOPLOCK().acquire.side_effect = None

    @patch('st2common.services.coordination.NoOpLock', MOCK_NOOPLOCK)
    def test_lock_decorator_eventually_succeed(self):
        MOCK_NOOPLOCK.reset_mock()
        MOCK_NOOPLOCK().acquire.side_effect = [False, False, True]
        lock_name = 'fakelock'

        @coordination.lock(lock_name)
        def _decorated():
            pass

        _decorated()

        self.assertEquals(MOCK_NOOPLOCK().acquire.call_count, 3)
        MOCK_NOOPLOCK().release.assert_called_once()

        MOCK_NOOPLOCK().acquire.return_value = True
        MOCK_NOOPLOCK().acquire.side_effect = None
