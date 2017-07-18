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

import os
import sys

import eventlet
from oslo_config import cfg
from eventlet import wsgi

from st2common import log as logging
from st2common.service_setup import setup as common_setup
from st2common.service_setup import teardown as common_teardown
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

# How much time to give to the request in progress to finish in seconds before killing them
WSGI_SERVER_REQUEST_SHUTDOWN_TIME = 2


def _setup():
    common_setup(service='api', config=config, setup_db=True, register_mq_exchanges=True,
                 register_signal_handlers=True, register_internal_trigger_types=True)

    # Additional pre-run time checks
    validate_rbac_is_correctly_configured()


def _run_server():
    host = cfg.CONF.api.host
    port = cfg.CONF.api.port

    LOG.info('(PID=%s) ST2 API is serving on http://%s:%s.', os.getpid(), host, port)

    max_pool_size = eventlet.wsgi.DEFAULT_MAX_SIMULTANEOUS_REQUESTS
    worker_pool = eventlet.GreenPool(max_pool_size)
    sock = eventlet.listen((host, port))

    wsgi.server(sock, app.setup_app(), custom_pool=worker_pool, log=LOG, log_output=False)
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
        LOG.exception('(PID=%s) ST2 API quit due to exception.', os.getpid())
        return 1
    finally:
        _teardown()
