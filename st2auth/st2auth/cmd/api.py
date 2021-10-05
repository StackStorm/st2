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

from st2common.util.monkey_patch import monkey_patch

monkey_patch()

import eventlet
import os
import sys

from oslo_config import cfg
from eventlet import wsgi

from st2common import log as logging
from st2common.service_setup import setup as common_setup
from st2common.service_setup import teardown as common_teardown
from st2auth import config

config.register_opts(ignore_errors=True)

from st2auth import app
from st2auth.validation import validate_auth_backend_is_correctly_configured


__all__ = ["main"]


LOG = logging.getLogger(__name__)


def _setup():
    capabilities = {
        "name": "auth",
        "listen_host": cfg.CONF.auth.host,
        "listen_port": cfg.CONF.auth.port,
        "listen_ssl": cfg.CONF.auth.use_ssl,
        "type": "active",
    }
    common_setup(
        service="auth",
        config=config,
        setup_db=True,
        register_mq_exchanges=False,
        register_signal_handlers=True,
        register_internal_trigger_types=False,
        run_migrations=False,
        service_registry=True,
        capabilities=capabilities,
    )

    # Additional pre-run time checks
    validate_auth_backend_is_correctly_configured()


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
        socket = eventlet.wrap_ssl(
            socket, certfile=cert_file_path, keyfile=key_file_path, server_side=True
        )

    LOG.info('ST2 Auth API running in "%s" auth mode', cfg.CONF.auth.mode)
    LOG.info(
        "(PID=%s) ST2 Auth API is serving on %s://%s:%s.",
        os.getpid(),
        "https" if use_ssl else "http",
        host,
        port,
    )

    wsgi.server(socket, app.setup_app(), log=LOG, log_output=False)
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
        LOG.exception("(PID=%s) ST2 Auth API quit due to exception.", os.getpid())
        return 1
    finally:
        _teardown()
