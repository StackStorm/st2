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

import eventlet
import Queue


class BufferedDispatcher(object):

    def __init__(self, dispatch_pool_size=50, monitor_thread_empty_q_sleep_time=5,
                 monitor_thread_no_workers_sleep_time=1):
        self._pool_limit = dispatch_pool_size
        self._dispatcher_pool = eventlet.GreenPool(dispatch_pool_size)
        self._dispatch_monitor_thread = eventlet.greenthread.spawn(self._flush)
        self._monitor_thread_empty_q_sleep_time = monitor_thread_empty_q_sleep_time
        self._monitor_thread_no_workers_sleep_time = monitor_thread_no_workers_sleep_time
        self._work_buffer = Queue.Queue()

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
            return
        while not self._work_buffer.empty() and self._dispatcher_pool.free() > 0:
            handler, args = self._work_buffer.get_nowait()
            self._dispatcher_pool.spawn(handler, *args)
