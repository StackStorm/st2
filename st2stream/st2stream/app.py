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

"""
Stream WSGI application.

This application listens for events on the RabbitMQ message bus and delivers them to all the
clients which are connected to the stream HTTP endpoint (fan out approach).

Note: This app doesn't need access to MongoDB, just RabbitMQ.
"""

from oslo_config import cfg

from st2stream import config as st2stream_config
from st2common import log as logging
from st2common.middleware.streaming import StreamingMiddleware
from st2common.middleware.error_handling import ErrorHandlingMiddleware
from st2common.middleware.cors import CorsMiddleware
from st2common.middleware.request_id import RequestIDMiddleware
from st2common.middleware.logging import LoggingMiddleware
from st2common.middleware.instrumentation import RequestInstrumentationMiddleware
from st2common.middleware.instrumentation import ResponseInstrumentationMiddleware
from st2common.router import Router
from st2common.constants.system import VERSION_STRING
from st2common.service_setup import setup as common_setup
from st2common.util import spec_loader

LOG = logging.getLogger(__name__)


def setup_app(config={}):
    LOG.info("Creating st2stream: %s as OpenAPI app.", VERSION_STRING)

    is_gunicorn = config.get("is_gunicorn", False)
    if is_gunicorn:

        st2stream_config.register_opts(ignore_errors=True)
        capabilities = {
            "name": "stream",
            "listen_host": cfg.CONF.stream.host,
            "listen_port": cfg.CONF.stream.port,
            "type": "active",
        }
        # This should be called in gunicorn case because we only want
        # workers to connect to db, rabbbitmq etc. In standalone HTTP
        # server case, this setup would have already occurred.
        common_setup(
            service="stream",
            config=st2stream_config,
            setup_db=True,
            register_mq_exchanges=True,
            register_signal_handlers=True,
            register_internal_trigger_types=False,
            run_migrations=False,
            service_registry=True,
            capabilities=capabilities,
            config_args=config.get("config_args", None),
        )

    router = Router(
        debug=cfg.CONF.stream.debug, auth=cfg.CONF.auth.enable, is_gunicorn=is_gunicorn
    )

    spec = spec_loader.load_spec("st2common", "openapi.yaml.j2")
    transforms = {"^/stream/v1/": ["/", "/v1/"]}
    router.add_spec(spec, transforms=transforms)

    app = router.as_wsgi

    # Order is important. Check middleware for detailed explanation.
    app = StreamingMiddleware(app)
    app = ErrorHandlingMiddleware(app)
    app = CorsMiddleware(app)
    app = LoggingMiddleware(app, router)
    app = ResponseInstrumentationMiddleware(app, router, service_name="stream")
    app = RequestIDMiddleware(app)
    app = RequestInstrumentationMiddleware(app, router, service_name="stream")

    return app
