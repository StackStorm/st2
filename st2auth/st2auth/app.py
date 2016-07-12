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

import pecan
from oslo_config import cfg

from st2auth import config as st2auth_config
from st2common import hooks
from st2common import log as logging
from st2common.util.monkey_patch import monkey_patch
from st2common.constants.system import VERSION_STRING
from st2common.service_setup import setup as common_setup

LOG = logging.getLogger(__name__)


def _get_pecan_config():

    config = {
        'app': {
            'root': 'st2auth.controllers.root.RootController',
            'modules': ['st2auth'],
            'debug': cfg.CONF.auth.debug,
            'errors': {'__force_dict__': True}
        }
    }

    return pecan.configuration.conf_from_dict(config)


def setup_app(config=None):
    LOG.info('Creating st2auth: %s as Pecan app.', VERSION_STRING)

    is_gunicorn = getattr(config, 'is_gunicorn', False)
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
                     config_args=config.config_args)

    if not config:
        # standalone HTTP server case
        config = _get_pecan_config()
    else:
        # gunicorn case
        if is_gunicorn:
            config.app = _get_pecan_config().app

    app_conf = dict(config.app)

    app = pecan.make_app(
        app_conf.pop('root'),
        logging=getattr(config, 'logging', {}),
        hooks=[hooks.JSONErrorResponseHook(), hooks.CorsHook(), hooks.AuthHook()],
        **app_conf
    )
    LOG.info('%s app created.' % __name__)

    return app
