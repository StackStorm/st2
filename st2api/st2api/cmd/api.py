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
from oslo.config import cfg
from eventlet import wsgi

from st2common import log as logging
from st2common.models.db import db_setup
from st2common.models.db import db_teardown
from st2common.constants.logging import DEFAULT_LOGGING_CONF_PATH
from st2common.transport.utils import register_exchanges
from st2api.listener import get_listener_if_set
from st2api import config
from st2api.app import get_api_app
from st2api.app import get_webui_app


eventlet.monkey_patch(
    os=True,
    select=True,
    socket=True,
    thread=False if '--use-debugger' in sys.argv else True,
    time=True)

LOG = logging.getLogger(__name__)


def _setup():
    # Set up logger which logs everything which happens during and before config
    # parsing to sys.stdout
    logging.setup(DEFAULT_LOGGING_CONF_PATH)

    # 1. parse args to setup config.
    config.parse_args()

    # 2. setup logging.
    logging.setup(cfg.CONF.api.logging)

    # 3. all other setup which requires config to be parsed and logging to
    # be correctly setup.
    username = cfg.CONF.database.username if hasattr(cfg.CONF.database, 'username') else None
    password = cfg.CONF.database.password if hasattr(cfg.CONF.database, 'password') else None
    db_setup(cfg.CONF.database.db_name, cfg.CONF.database.host, cfg.CONF.database.port,
             username=username, password=password)
    register_exchanges()


def _run_server():
    host = cfg.CONF.api.host
    port = cfg.CONF.api.port

    api_host = cfg.CONF.api.host
    api_port = cfg.CONF.api.port

    webui_host = api_host
    webui_port = int(api_port) + 1

    LOG.info('(PID=%s) ST2 API is serving on http://%s:%s.', os.getpid(), api_host, api_port)
    LOG.info('(PID=%s) ST2 WebUI is serving on http://%s:%s.', os.getpid(), webui_host, webui_port)

    def _run_api_server():
        wsgi.server(eventlet.listen((api_host, api_port)), get_api_app())

    def _run_webui_server():
        wsgi.server(eventlet.listen((webui_host, webui_port)), get_webui_app())

    api_thread = eventlet.spawn(_run_api_server)
    webui_thread = eventlet.spawn(_run_webui_server)

    return (api_thread.wait() and webui_thread.wait())


def _teardown():
    db_teardown()


def main():
    try:
        _setup()
        return _run_server()
    except SystemExit as exit_code:
        sys.exit(exit_code)
    except KeyboardInterrupt:
        listener = get_listener_if_set()

        if listener:
            listener.shutdown()
    except:
        LOG.exception('(PID=%s) ST2 API quit due to exception.', os.getpid())
        return 1
    finally:
        _teardown()
