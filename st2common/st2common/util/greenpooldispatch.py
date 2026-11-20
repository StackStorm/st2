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
import time

from st2common.util import concurrency

from st2common import log as logging

__all__ = ["BufferedDispatcher"]

# If the thread pool has been occupied with no empty threads for more than this number of seconds
# a message will be logged
POOL_BUSY_THRESHOLD_SECONDS = 60

# How often a caller waiting for a free slot checks whether the dispatcher has been shut down
SLOT_WAIT_INTERVAL_SECONDS = 1

POOL_BUSY_LOG_MESSAGE = """
BufferedDispatcher pool "%s" has been busy with no free threads for more than %s seconds. If there \
are server resources available, consider increasing the dispatcher pool size in the config.
""".strip()

LOG = logging.getLogger(__name__)


class BufferedDispatcher(object):
    """
    Runs work items in green threads, with at most ``dispatch_pool_size`` running at once.

    Callers reserve a slot with ``acquire()`` and then hand the work over with ``dispatch()``.
    ``acquire()`` blocks while all the slots are in use, which lets a queue consumer stop
    pulling messages from the broker (instead of buffering them in memory) until a slot frees up.
    """

    def __init__(self, dispatch_pool_size=50, name=None):
        self._pool_limit = dispatch_pool_size
        self._slots = concurrency.Semaphore(dispatch_pool_size)
        self._in_use = 0
        self._shutdown = False
        self._name = name

    @property
    def name(self):
        return self._name or id(self)

    @property
    def free_count(self):
        return self._pool_limit - self._in_use

    def acquire(self):
        """
        Reserve a slot, blocking while all the slots are in use.

        :return: ``True`` if a slot was reserved, ``False`` if the dispatcher was shut down
                 before a slot became available.
        :rtype: ``bool``
        """
        busy_since = time.time()

        while not self._shutdown:
            if self._slots.acquire(timeout=SLOT_WAIT_INTERVAL_SECONDS):
                if self._shutdown:
                    self._slots.release()
                    return False

                self._in_use += 1
                return True

            if (time.time() - busy_since) >= POOL_BUSY_THRESHOLD_SECONDS:
                LOG.info(
                    POOL_BUSY_LOG_MESSAGE % (self.name, POOL_BUSY_THRESHOLD_SECONDS)
                )
                busy_since = time.time()

        return False

    def release(self):
        """
        Release a slot reserved with ``acquire()`` which won't be used for ``dispatch()``.
        """
        self._in_use -= 1
        self._slots.release()

    def dispatch(self, handler, *args):
        """
        Run the handler in a new green thread. The caller must have reserved a slot with
        ``acquire()``, the slot is released once the handler returns.
        """
        return concurrency.spawn(self._run, handler, *args)

    def shutdown(self):
        """
        Stop handing out slots. Callers blocked in ``acquire()`` return ``False``. Work which is
        already running is not interrupted.
        """
        self._shutdown = True

    def _run(self, handler, *args):
        try:
            handler(*args)
        finally:
            self.release()

    def __repr__(self):
        values = (
            self.name,
            self._pool_limit,
            self.free_count,
        )
        return (
            "<BufferedDispatcher name=%s,dispatch_pool_size=%s,free_threads=%s>"
            % values
        )
