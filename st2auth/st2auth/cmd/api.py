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
import sys

from oslo_config import cfg
from eventlet import wsgi

from st2common import log as logging
from st2common.service_setup import setup as common_setup
from st2common.service_setup import teardown as common_teardown
from st2common.constants.auth import VALID_MODES
from st2auth import config
from st2auth import app


eventlet.monkey_patch(
    os=True,
    select=True,
    socket=True,
    thread=False if '--use-debugger' in sys.argv else True,
    time=True)

LOG = logging.getLogger(__name__)


def _setup():
    common_setup(service='auth', config=config, setup_db=True, register_mq_exchanges=False,
                 register_signal_handlers=True, register_internal_trigger_types=False,
                 run_migrations=False)

    if cfg.CONF.auth.mode not in VALID_MODES:
        raise ValueError('Valid modes are: %s' % (','.join(VALID_MODES)))


def _run_server():
    host = cfg.CONF.auth.host
    port = cfg.CONF.auth.port
    use_ssl = cfg.CONF.auth.use_ssl

    cert_file_path = os.path.realpath(cfg.CONF.auth.cert)
    key_file_path = os.path.realpath(cfg.CONF.auth.key)

    if use_ssl and not os.path.isfile(cert_file_path):
        raise ValueError('Certificate file "%s" doesn\'t exist' % (cert_file_path))

    if use_ssl and not os.path.isfile(key_file_path):
        raise ValueError('Private key file "%s" doesn\'t exist' % (key_file_path))

    socket = eventlet.listen((host, port))

    if use_ssl:
        socket = eventlet.wrap_ssl(socket,
                                   certfile=cert_file_path,
                                   keyfile=key_file_path,
                                   server_side=True)

    LOG.info('ST2 Auth API running in "%s" auth mode', cfg.CONF.auth.mode)
    LOG.info('(PID=%s) ST2 Auth API is serving on %s://%s:%s.', os.getpid(),
             'https' if use_ssl else 'http', host, port)

    wsgi.server(socket, app.setup_app(run_common_setup=False))
    return 0


def _teardown():
    common_teardown()


def main():
    try:
        _setup()
        return _run_server()
    except SystemExit as exit_code:
        sys.exit(exit_code)
    except Exception:
        LOG.exception('(PID=%s) ST2 Auth API quit due to exception.', os.getpid())
        return 1
    finally:
        _teardown()
