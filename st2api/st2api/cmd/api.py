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
from st2common.models.db import db_teardown
from st2api.listener import get_listener_if_set
from st2api import wsgi as app


eventlet.monkey_patch(
    os=True,
    select=True,
    socket=True,
    thread=False if '--use-debugger' in sys.argv else True,
    time=True)

LOG = logging.getLogger(__name__)


def _run_server():
    host = cfg.CONF.api.host
    port = cfg.CONF.api.port

    LOG.info('(PID=%s) ST2 API is serving on http://%s:%s.', os.getpid(), host, port)

    wsgi.server(eventlet.listen((host, port)), app.setup())
    return 0


def _teardown():
    db_teardown()


def main():
    try:
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
