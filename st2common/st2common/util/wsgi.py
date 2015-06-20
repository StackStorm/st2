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

"""
Eventlet WSGI server related utility functions.
"""

import eventlet

from st2common import log as logging

LOG = logging.getLogger(__name__)

__all__ = [
    'shutdown_server_kill_pending_requests'
]


def shutdown_server_kill_pending_requests(sock, worker_pool, wait_time=2):
    """
    Custom WSGI server shutdown function which gives outgoing requests some time to finish
    before killing them.

    Without that, long running requests such as stream block and prevent server from shutting down.

    :param sock: WSGI server socket.
    :param worker_pool: WSGI server worker pool.
    :param wait_time: How long to give to the active requests to finish processing before
                      forcefully killing them.
    :type wait_time: ``int``
    """
    worker_pool.resize(0)
    sock.close()

    LOG.info('Shutting down. Requests left: %s', worker_pool.running())

    # Give running requests some time to finish
    eventlet.sleep(wait_time)

    # Kill requests which still didn't finish
    running_corutines = worker_pool.coroutines_running.copy()
    for coro in running_corutines:
        eventlet.greenthread.kill(coro)

    LOG.info('Exiting...')
    raise SystemExit()
