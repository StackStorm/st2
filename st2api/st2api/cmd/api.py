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
from oslo_config import cfg
from eventlet import wsgi

from st2common import log as logging
from st2common.service import ActiveService
from st2common.service import run_service
from st2common.util.monkey_patch import monkey_patch
from st2api import config
config.register_opts()
from st2api import app

from st2api.validation import validate_rbac_is_correctly_configured

__all__ = [
    'main'
]

monkey_patch()

LOG = logging.getLogger(__name__)


class APIHTTPService(ActiveService):
    name = 'api'
    config = config

    setup_db = True
    register_mq_exchanges = True
    register_signal_handlers = True
    register_internal_trigger_types = True
    run_migrations = True

    def setup(self):
        super(APIHTTPService, self).setup()

        # Additional pre-run time checks
        validate_rbac_is_correctly_configured()

    def start(self):
        super(APIHTTPService, self).start()

        max_pool_size = eventlet.wsgi.DEFAULT_MAX_SIMULTANEOUS_REQUESTS
        worker_pool = eventlet.GreenPool(max_pool_size)
        self._socket = eventlet.listen((self._host, self._port))

        self.logger.info('(PID=%s) StackStorm API is serving on http://%s:%s.', self.pid,
                         self._host, self._port)

        wsgi_app = app.setup_app()
        self._server = wsgi.server(self._socket, wsgi_app, custom_pool=worker_pool, log=LOG,
                                   log_output=False)


def main():
    service = APIHTTPService(logger=LOG, host=cfg.CONF.api.host, port=cfg.CONF.api.port)
    exit_code = run_service(service=service)
    return exit_code
