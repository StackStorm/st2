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
import pkg_resources

import jinja2
from oslo_config import cfg
from pecan.middleware.static import StaticFileMiddleware
import yaml

from st2api import config as st2api_config
from st2common import constants
from st2common import log as logging
from st2common.router import Router, ErrorHandlingMiddleware
from st2common.util.monkey_patch import monkey_patch
from st2common.constants.system import VERSION_STRING
from st2common.service_setup import setup as common_setup
from st2common.util import isotime

LOG = logging.getLogger(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def setup_app(config=None):
    LOG.info('Creating st2api: %s as OpenAPI app.', VERSION_STRING)

    is_gunicorn = getattr(config, 'is_gunicorn', False)
    if is_gunicorn:
        # Note: We need to perform monkey patching in the worker. If we do it in
        # the master process (gunicorn_config.py), it breaks tons of things
        # including shutdown
        monkey_patch()

        st2api_config.register_opts()
        # This should be called in gunicorn case because we only want
        # workers to connect to db, rabbbitmq etc. In standalone HTTP
        # server case, this setup would have already occurred.
        common_setup(service='api', config=st2api_config, setup_db=True,
                     register_mq_exchanges=True,
                     register_signal_handlers=True,
                     register_internal_trigger_types=True,
                     run_migrations=True,
                     config_args=config.config_args)

    # active_hooks = [hooks.RequestIDHook(), hooks.JSONErrorResponseHook(),
    #                 hooks.LoggingHook()]

    # active_hooks.append(hooks.CorsHook())

    arguments = {
        'DEFAULT_PACK_NAME': constants.pack.DEFAULT_PACK_NAME,
        'LIVEACTION_STATUSES': constants.action.LIVEACTION_STATUSES,
        'ISO8601_UTC_REGEX': isotime.ISO8601_UTC_REGEX
    }

    spec_template = pkg_resources.resource_string(__name__, 'controllers/openapi.yaml')
    spec_string = jinja2.Template(spec_template).render(**arguments)
    spec = yaml.load(spec_string)

    router = Router(debug=cfg.CONF.api.debug, auth=cfg.CONF.auth.enable)
    router.add_spec(spec)

    app = router.as_wsgi

    app = ErrorHandlingMiddleware(app)

    # Static middleware which servers common static assets such as logos
    static_root = os.path.join(BASE_DIR, 'public')
    app = StaticFileMiddleware(app=app, directory=static_root)

    LOG.info('%s app created.' % __name__)
    return app
