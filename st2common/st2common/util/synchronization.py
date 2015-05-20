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

import eventlet

from st2common import log as logging
from st2common.exceptions import db as db_exc
from st2common.exceptions import synchronization as sync_exc
from st2common.models.db import synchronization as models
from st2common.persistence import synchronization as persistence
from st2common.util import system_info


LOG = logging.getLogger(__name__)


class Lock(object):

    def __init__(self, lock):
        self._lock = lock

    @classmethod
    def acquire(cls, name, expires=60, timeout=180):
        lock = models.LockDB(name=name,
                             owner=uuid.uuid4().hex,
                             proc_info=system_info.get_process_info(),
                             expiry=(datetime.datetime.utcnow() +
                                     datetime.timedelta(seconds=expires)))

        dt_timeout = datetime.datetime.utcnow() + datetime.timedelta(seconds=timeout)

        while True:
            try:
                return cls(persistence.Lock.add(lock))
            except db_exc.StackStormDBObjectConflictError:
                LOG.warn('Unable to acquire lock for %s because it is in use.', name)

            if dt_timeout <= datetime.datetime.utcnow():
                raise sync_exc.LockTimeoutError('Timed out waiting to acquire lock for %s.', name)

            eventlet.sleep(1)

        LOG.debug('Acquired lock for %s.', name)

    def release(self):
        try:
            persistence.Lock.delete(self._lock)
        except db_exc.StackStormDBObjectFoundError:
            raise sync_exc.LockReleaseError('Lock still exists.')

        LOG.debug('Released lock for %s.', self._lock.name)
