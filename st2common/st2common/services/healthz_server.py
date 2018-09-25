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
from eventlet import wsgi

from st2common import log as logging

__all__ = [
    'HealthZHTTPServer'
]

LOG = logging.getLogger(__name__)


def handle_request(env, start_response):
    path_info = env['PATH_INFO']

    if path_info == '/healthz':
        start_response('200 SUCCESS', [('Content-Type', 'application/json')])
        return ''
    else:
        start_response('404 NOT FOUND', [('Content-Type', 'text/plain')])
        return ''


class HealthZHTTPServer(object):
    """
    HTTP server which exposes service health information over an HTTP interface.

    NOTE: This server is doesn't run behind any authentication so it only listens on localhost by
    default.
    """

    def __init__(self, host='127.0.0.1', port=5555):
        self._host = host
        self._port = port

        self._started = False

        self._sock = None
        self._server = None

    def start(self):
        LOG.info('Healthz HTTP endpoint listening on %s:%s' % (self._host, self._port))

        self._sock = eventlet.listen((self._host, self._port))
        self._server = wsgi.server(self._sock, handle_request, log=LOG, log_output=False)

    def stop(self):
        self._started = False
