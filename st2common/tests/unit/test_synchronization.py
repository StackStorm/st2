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

import datetime
import uuid

from st2common.exceptions import db as db_exc
from st2common.exceptions import synchronization as sync_exc
from st2common.persistence import synchronization as persistence
from st2common.util.synchronization import Lock
from st2common.util import system_info
from st2tests.base import DbTestCase


class SynchronizationTest(DbTestCase):

    def test_lock(self):
        name = uuid.uuid4().hex
        expire_in_sec = 10

        # Acquire lock.
        lock = Lock.acquire(name, expires=expire_in_sec)
        self.assertIsNotNone(lock)
        self.assertIsNotNone(lock._lock)
        self.assertEqual(lock._lock.name, name)
        self.assertDictEqual(lock._lock.proc_info, system_info.get_process_info())
        self.assertIsNotNone(lock._lock.owner)
        expire_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=expire_in_sec)
        self.assertLessEqual(lock._lock.expiry, expire_at)

        # Query lock and ensure owner info is not loaded.
        copy = persistence.Lock.get_by_name(name)
        self.assertEqual(copy.id, lock._lock.id)
        self.assertIsNone(getattr(copy, 'owner', None))

        # Release lock.
        lock.release()
        self.assertRaises(ValueError, persistence.Lock.get_by_name, name)

    def test_multiple_acquire(self):
        name = uuid.uuid4().hex
        expire_in_sec = 60
        timeout_in_sec = 1

        # Acquire lock.
        lock1 = Lock.acquire(name, expires=expire_in_sec)

        # Error is expected if trying to acquire lock again.
        self.assertRaises(sync_exc.LockTimeoutError, Lock.acquire, name, timeout=timeout_in_sec)

        # Error is expected if not using the release method to unlock.
        lock_db = persistence.Lock.get_by_name(name)
        self.assertRaises(db_exc.StackStormDBObjectFoundError, persistence.Lock.delete, lock_db)

        # Release lock.
        lock1.release()
        self.assertRaises(ValueError, persistence.Lock.get_by_name, name)

        # Acquire lock again.
        lock2 = Lock.acquire(name, expires=expire_in_sec)
        self.assertNotEqual(lock1._lock.id, lock2._lock.id)
        self.assertNotEqual(lock1._lock.owner, lock2._lock.owner)

        # Error is expected if previous lock tries to release.
        self.assertRaises(sync_exc.LockReleaseError, lock1.release)
