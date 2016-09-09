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

import time

import eventlet
import Queue

from st2common import log as logging

__all__ = [
    'BufferedDispatcher'
]

# If the thread pool has been occupied with no empty threads for more than this number of seconds
# a message will be logged
POOL_BUSY_THRESHOLD_SECONDS = 60

POOL_BUSY_LOG_MESSAGE = """
BufferedDispatcher pool "%s" has been busy with no free threads for more than %s seconds. If there \
are server resources available, consider increasing the dispatcher pool size in the config.
""".strip()

LOG = logging.getLogger(__name__)


class BufferedDispatcher(object):

    def __init__(self, dispatch_pool_size=50, monitor_thread_empty_q_sleep_time=5,
                 monitor_thread_no_workers_sleep_time=1, name=None):
        self._pool_limit = dispatch_pool_size
        self._dispatcher_pool = eventlet.GreenPool(dispatch_pool_size)
        self._dispatch_monitor_thread = eventlet.greenthread.spawn(self._flush)
        self._monitor_thread_empty_q_sleep_time = monitor_thread_empty_q_sleep_time
        self._monitor_thread_no_workers_sleep_time = monitor_thread_no_workers_sleep_time
        self._name = name

        self._work_buffer = Queue.Queue()

        # Internal attributes we use to track how long the pool is busy without any free workers
        self._pool_last_free_ts = time.time()

    @property
    def name(self):
        return self._name or id(self)

    def dispatch(self, handler, *args):
        self._work_buffer.put((handler, args), block=True, timeout=1)
        self._flush_now()

    def shutdown(self):
        self._dispatch_monitor_thread.kill()

    def _flush(self):
        while True:
            while self._work_buffer.empty():
                eventlet.greenthread.sleep(self._monitor_thread_empty_q_sleep_time)
            while self._dispatcher_pool.free() <= 0:
                eventlet.greenthread.sleep(self._monitor_thread_no_workers_sleep_time)
            self._flush_now()

    def _flush_now(self):
        if self._dispatcher_pool.free() <= 0:
            now = time.time()

            if (now - self._pool_last_free_ts) >= POOL_BUSY_THRESHOLD_SECONDS:
                LOG.info(POOL_BUSY_LOG_MESSAGE % (self.name, POOL_BUSY_THRESHOLD_SECONDS))

            return

        # Update the time of when there were free threads available
        self._pool_last_free_ts = time.time()

        while not self._work_buffer.empty() and self._dispatcher_pool.free() > 0:
            (handler, args) = self._work_buffer.get_nowait()
            self._dispatcher_pool.spawn(handler, *args)

    def __repr__(self):
        free_count = self._dispatcher_pool.free()
        values = (self.name, self._pool_limit, free_count, self._monitor_thread_empty_q_sleep_time,
                  self._monitor_thread_no_workers_sleep_time)
        return ('<BufferedDispatcher name=%s,dispatch_pool_size=%s,free_threads=%s,'
                'monitor_thread_empty_q_sleep_time=%s,monitor_thread_no_workers_sleep_time=%s>' %
                values)
