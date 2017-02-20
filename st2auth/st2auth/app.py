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

import pkg_resources

import jinja2
from oslo_config import cfg
import yaml

from st2auth import config as st2auth_config
import st2common.constants.pack
import st2common.constants.action
from st2common import log as logging
from st2common.middleware.error_handling import ErrorHandlingMiddleware
from st2common.middleware.cors import CorsMiddleware
from st2common.middleware.request_id import RequestIDMiddleware
from st2common.middleware.logging import LoggingMiddleware
from st2common.rbac.types import PermissionType
from st2common.router import Router
from st2common.util.monkey_patch import monkey_patch
from st2common.constants.system import VERSION_STRING
from st2common.service_setup import setup as common_setup
from st2common.util import isotime

LOG = logging.getLogger(__name__)


def setup_app(config={}):
    LOG.info('Creating st2auth: %s as OpenAPI app.', VERSION_STRING)

    is_gunicorn = config.get('is_gunicorn', False)
    if is_gunicorn:
        # Note: We need to perform monkey patching in the worker. If we do it in
        # the master process (gunicorn_config.py), it breaks tons of things
        # including shutdown
        monkey_patch()

        # This should be called in gunicorn case because we only want
        # workers to connect to db, rabbbitmq etc. In standalone HTTP
        # server case, this setup would have already occurred.
        st2auth_config.register_opts()
        common_setup(service='auth', config=st2auth_config, setup_db=True,
                     register_mq_exchanges=False,
                     register_signal_handlers=True,
                     register_internal_trigger_types=False,
                     run_migrations=False,
                     config_args=config.get('config_args', None))

    arguments = {
        'DEFAULT_PACK_NAME': st2common.constants.pack.DEFAULT_PACK_NAME,
        'LIVEACTION_STATUSES': st2common.constants.action.LIVEACTION_STATUSES,
        'PERMISSION_TYPE': PermissionType,
        'ISO8601_UTC_REGEX': isotime.ISO8601_UTC_REGEX
    }

    router = Router(debug=cfg.CONF.auth.debug)

    spec_template = pkg_resources.resource_string(__name__, 'controllers/openapi.yaml')
    spec_string = jinja2.Template(spec_template).render(**arguments)
    spec = yaml.load(spec_string)

    router.add_spec(spec)

    app = router.as_wsgi

    app = CorsMiddleware(app)
    app = LoggingMiddleware(app, router)
    app = ErrorHandlingMiddleware(app)
    app = RequestIDMiddleware(app)

    return app
