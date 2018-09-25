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
import os

from oslo_config import cfg
from eventlet import wsgi

from st2common import log as logging
from st2common.service import ActiveService
from st2common.service import run_service
from st2common.util.monkey_patch import monkey_patch
from st2auth import config
config.register_opts()

from st2auth import app
from st2auth.validation import validate_auth_backend_is_correctly_configured


__all__ = [
    'main'
]

monkey_patch()

LOG = logging.getLogger(__name__)


class AuthAPIHTTPService(ActiveService):
    name = 'auth'
    config = config

    setup_db = True
    register_mq_exchanges = False
    register_signal_handlers = True
    register_internal_trigger_types = False
    run_migrations = False

    def setup(self):
        super(AuthAPIHTTPService, self).setup()

        # Additional pre-run time checks
        validate_auth_backend_is_correctly_configured()

    def start(self):
        super(AuthAPIHTTPService, self).start()

        use_ssl = cfg.CONF.auth.use_ssl

        cert_file_path = os.path.realpath(cfg.CONF.auth.cert)
        key_file_path = os.path.realpath(cfg.CONF.auth.key)

        if use_ssl and not os.path.isfile(cert_file_path):
            raise ValueError('Certificate file "%s" doesn\'t exist' % (cert_file_path))

        if use_ssl and not os.path.isfile(key_file_path):
            raise ValueError('Private key file "%s" doesn\'t exist' % (key_file_path))

        self._socket = eventlet.listen((self._host, self._port))

        if use_ssl:
            self._socket = eventlet.wrap_ssl(self.socket,
                                             certfile=cert_file_path,
                                             keyfile=key_file_path,
                                             server_side=True)

        self.logger.info('StackStorm Auth API running in "%s" auth mode', cfg.CONF.auth.mode)
        self.logger.info('(PID=%s) StackStorm Auth API is serving on %s://%s:%s.', self.pid,
                         'https' if use_ssl else 'http', self._host, self._port)

        wsgi_app = app.setup_app()
        self._server = wsgi.server(self._socket, wsgi_app, log=LOG, log_output=False)


def main():
    service = AuthAPIHTTPService(logger=LOG, host=cfg.CONF.auth.host, port=cfg.CONF.auth.port)
    exit_code = run_service(service=service)
    return exit_code
