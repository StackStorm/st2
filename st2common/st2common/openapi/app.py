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

from oslo_config import cfg

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
from st2common.util.monkey_patch import use_select_poll_workaround

LOG = logging.getLogger(__name__)


def setup(
    service_name,
    app_config,
    oslo_cfg,
    common_setup_kwargs={},
):
    capabilities = {
        "name": service_name,
        "listen_host": oslo_cfg.host,
        "listen_port": oslo_cfg.port,
        "listen_ssl": oslo_cfg.use_ssl,
        "type": "active",
    }

    # This should be called in gunicorn case because we only want
    # workers to connect to db, rabbbitmq etc. In standalone HTTP
    # server case, this setup would have already occurred.
    common_setup(
        service=service_name,
        config=app_config,
        setup_db=True,
        register_signal_handlers=True,
        service_registry=True,
        capabilities=capabilities,
        **common_setup_kwargs,
    )


def run_pre_run_checks(pre_run_checks=[]):
    # Additional pre-run time checks
    for pre_run_check in pre_run_checks:
        pre_run_check()


def setup_app(
    service_name,
    app_config,
    oslo_cfg,
    pre_run_checks=[],
    transforms={},
    common_setup_kwargs={},
    path_whitelist=[],
    config={},
):
    LOG.info("Creating st2%s: %s as OpenAPI app.", service_name, VERSION_STRING)

    is_gunicorn = config.get("is_gunicorn", False)
    if is_gunicorn:
        # NOTE: We only want to perform this logic in the WSGI worker
        app_config.register_opts(ignore_errors=True)

        common_setup_kwargs["config_args"] = config.get("config_args", None)
        setup(
            service_name=service_name,
            app_config=app_config,
            oslo_cfg=oslo_cfg,
            common_setup_kwargs=common_setup_kwargs,
        )

        if service_name == "auth":
            # pysaml2 uses subprocess communicate which calls communicate_with_poll
            if oslo_cfg.sso and oslo_cfg.sso_backend == "saml2":
                use_select_poll_workaround(nose_only=False)

    run_pre_run_checks(pre_run_checks=pre_run_checks)

    auth = True

    if service_name != "auth":
        auth = cfg.CONF.auth.enable

    router = Router(debug=oslo_cfg.debug, is_gunicorn=is_gunicorn, auth=auth)

    spec = spec_loader.load_spec("st2common", "openapi.yaml.j2")
    router.add_spec(spec, transforms=transforms)

    app = router.as_wsgi

    # Order is important. Check middleware for detailed explanation.
    if service_name != "auth":
        app = StreamingMiddleware(app, path_whitelist=path_whitelist)

    app = ErrorHandlingMiddleware(app)
    app = CorsMiddleware(app)
    app = LoggingMiddleware(app, router)
    app = ResponseInstrumentationMiddleware(app, router, service_name=service_name)
    app = RequestIDMiddleware(app)
    app = RequestInstrumentationMiddleware(app, router, service_name=service_name)

    return app
