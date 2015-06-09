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

import unittest2
import uuid

from oslo.config import cfg

from st2common.services import coordination
import st2tests.config as tests_config


class SynchronizationTest(unittest2.TestCase):
    coordinator = None

    @classmethod
    def setUpClass(cls):
        super(SynchronizationTest, cls).setUpClass()
        tests_config.parse_args()
        cls.coordinator = coordination.get_coordinator()

    @classmethod
    def tearDownClass(cls):
        coordination.coordinator_teardown(cls.coordinator)
        super(SynchronizationTest, cls).tearDownClass()

    def test_service_configured(self):
        cfg.CONF.set_default('url', 'kazoo://localhost:2181', group='coordination')
        self.assertTrue(coordination.configured())

        cfg.CONF.set_default('url', 'file:///tmp', group='coordination')
        self.assertFalse(coordination.configured())

        cfg.CONF.set_default('url', 'zake://', group='coordination')
        self.assertFalse(coordination.configured())

    def test_lock(self):
        name = uuid.uuid4().hex

        # Acquire lock.
        lock = self.coordinator.get_lock(name)
        self.assertTrue(lock.acquire())

        # Release lock.
        lock.release()

    def test_multiple_acquire(self):
        name = uuid.uuid4().hex

        # Acquire lock.
        lock1 = self.coordinator.get_lock(name)
        self.assertTrue(lock1.acquire())

        # Error is expected if trying to acquire lock again.
        lock2 = self.coordinator.get_lock(name)
        self.assertFalse(lock2.acquire(blocking=False))

        # Release from the first lock instance.
        lock1.release()

        # Acquire the lock again from the second lock instance.
        self.assertTrue(lock2.acquire())

        # Release from the second lock instance.
        lock2.release()

    def test_lock_expiry_on_session_close(self):
        name = uuid.uuid4().hex

        # Acquire lock.
        lock1 = self.coordinator.get_lock(name)
        self.assertTrue(lock1.acquire())

        # Error is expected if trying to acquire lock again.
        lock2 = self.coordinator.get_lock(name)
        self.assertFalse(lock2.acquire(blocking=False))

        # Recycle the session.
        self.coordinator.stop()
        self.coordinator.start()

        # Acquire lock.
        lock3 = self.coordinator.get_lock(name)
        self.assertTrue(lock3.acquire())
        lock3.release()
