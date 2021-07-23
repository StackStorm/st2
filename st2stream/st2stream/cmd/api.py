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

import os
import sys

import eventlet
from oslo_config import cfg
from eventlet import wsgi

from st2common import log as logging
from st2common.service_setup import setup as common_setup
from st2common.service_setup import teardown as common_teardown
from st2common.stream.listener import get_listener_if_set
from st2common.util.wsgi import shutdown_server_kill_pending_requests
from st2stream.signal_handlers import register_stream_signal_handlers
from st2stream import config

config.register_opts(ignore_errors=True)

from st2stream import app

__all__ = ["main"]


eventlet.monkey_patch(
    os=True,
    select=True,
    socket=True,
    thread=False if "--use-debugger" in sys.argv else True,
    time=True,
)

LOG = logging.getLogger(__name__)

# How much time to give to the request in progress to finish in seconds before killing them
WSGI_SERVER_REQUEST_SHUTDOWN_TIME = 2


def _setup():
    capabilities = {
        "name": "stream",
        "listen_host": cfg.CONF.stream.host,
        "listen_port": cfg.CONF.stream.port,
        "type": "active",
    }
    common_setup(
        service="stream",
        config=config,
        setup_db=True,
        register_mq_exchanges=True,
        register_signal_handlers=True,
        register_internal_trigger_types=False,
        run_migrations=False,
        service_registry=True,
        capabilities=capabilities,
    )


def _run_server():
    host = cfg.CONF.stream.host
    port = cfg.CONF.stream.port

    LOG.info(
        "(PID=%s) ST2 Stream API is serving on http://%s:%s.", os.getpid(), host, port
    )

    max_pool_size = eventlet.wsgi.DEFAULT_MAX_SIMULTANEOUS_REQUESTS
    worker_pool = eventlet.GreenPool(max_pool_size)
    sock = eventlet.listen((host, port))

    def queue_shutdown(signal_number, stack_frame):
        eventlet.spawn_n(
            shutdown_server_kill_pending_requests,
            sock=sock,
            worker_pool=worker_pool,
            wait_time=WSGI_SERVER_REQUEST_SHUTDOWN_TIME,
        )

    # We register a custom SIGINT handler which allows us to kill long running active requests.
    # Note: Eventually we will support draining (waiting for short-running requests), but we
    # will still want to kill long running stream requests.
    register_stream_signal_handlers(handler_func=queue_shutdown)

    wsgi.server(sock, app.setup_app(), custom_pool=worker_pool)
    return 0


def _teardown():
    common_teardown()


def main():
    try:
        _setup()
        return _run_server()
    except SystemExit as exit_code:
        sys.exit(exit_code)
    except KeyboardInterrupt:
        listener = get_listener_if_set(name="stream")

        if listener:
            listener.shutdown()
    except Exception:
        LOG.exception("(PID=%s) ST2 Stream API quit due to exception.", os.getpid())
        return 1
    finally:
        _teardown()
