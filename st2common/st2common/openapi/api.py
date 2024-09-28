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

import eventlet
import os
import sys

from eventlet import wsgi

from st2common.openapi import app as common_app
from st2common.service_setup import deregister_service
from st2common.service_setup import teardown as common_teardown
from st2common.stream.listener import get_listener_if_set
from st2common.util.wsgi import shutdown_server_kill_pending_requests
from st2stream.signal_handlers import register_stream_signal_handlers


def run_server(
    service_name, cfg, app, log=None, log_output=True, use_custom_pool=False
):
    host = cfg.host
    port = cfg.port
    use_ssl = cfg.use_ssl

    cert_file_path = os.path.realpath(cfg.cert)
    key_file_path = os.path.realpath(cfg.key)

    if use_ssl and not os.path.isfile(cert_file_path):
        raise ValueError('Certificate file "%s" doesn\'t exist' % (cert_file_path))

    if use_ssl and not os.path.isfile(key_file_path):
        raise ValueError('Private key file "%s" doesn\'t exist' % (key_file_path))

    worker_pool = None
    if use_custom_pool:
        max_pool_size = eventlet.wsgi.DEFAULT_MAX_SIMULTANEOUS_REQUESTS
        worker_pool = eventlet.GreenPool(max_pool_size)

    socket = eventlet.listen((host, port))

    if use_ssl:
        socket = eventlet.wrap_ssl(
            socket, certfile=cert_file_path, keyfile=key_file_path, server_side=True
        )

    if service_name == "auth":
        log.info('ST2 Auth API running in "%s" auth mode', cfg.mode)

    if service_name == "stream":

        def queue_shutdown(signal_number, stack_frame):
            deregister_service(service_name)
            eventlet.spawn_n(
                shutdown_server_kill_pending_requests,
                sock=socket,
                worker_pool=worker_pool,
                wait_time=2,
            )

        # We register a custom SIGINT handler which allows us to kill long running active requests.
        # Note: Eventually we will support draining (waiting for short-running requests), but we
        # will still want to kill long running stream requests.
        register_stream_signal_handlers(handler_func=queue_shutdown)

    log.info(
        "(PID=%s) ST2 %s API is serving on %s://%s:%s.",
        os.getpid(),
        service_name,
        "https" if use_ssl else "http",
        host,
        port,
    )

    wsgi.server(
        socket, app.setup_app(), custom_pool=worker_pool, log=log, log_output=log_output
    )

    return 0


def run(
    service_name,
    app_config,
    cfg,
    app,
    log,
    use_custom_pool=False,
    log_output=True,
    common_setup_kwargs={},
    pre_run_checks=[],
):
    try:
        common_app.setup(
            service_name=service_name,
            app_config=app_config,
            oslo_cfg=cfg,
            common_setup_kwargs=common_setup_kwargs,
        )
        common_app.run_pre_run_checks(pre_run_checks=pre_run_checks)
        return run_server(
            service_name=service_name,
            cfg=cfg,
            app=app,
            log=log,
            use_custom_pool=use_custom_pool,
            log_output=log_output,
        )
    except SystemExit as exit_code:
        deregister_service(service_name)

        if service_name == "stream":
            listener = get_listener_if_set(name=service_name)

            if listener:
                listener.shutdown()
        else:
            sys.exit(exit_code)
    except Exception:
        log.exception(
            "(PID=%s) ST2 %s API quit due to exception.", os.getpid(), service_name
        )
        return 1
    finally:
        common_teardown()
