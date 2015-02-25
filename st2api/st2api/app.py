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
from oslo.config import cfg

from st2common import hooks
from st2common import log as logging
from st2common.constants.system import VERSION_STRING

__all__ = [
    'get_api_app',
    'get_webui_app'
]


LOG = logging.getLogger(__name__)


def __get_pecan_config():
    opts = cfg.CONF.api_pecan

    cfg_dict = {
        'app': {
            'root': opts.root,
            'template_path': opts.template_path,
            'modules': opts.modules,
            'debug': False,
            'auth_enable': opts.auth_enable,
            'errors': opts.errors
        }
    }

    return pecan.configuration.conf_from_dict(cfg_dict)


def get_api_app(config=None):
    LOG.info(VERSION_STRING)

    LOG.info('Creating %s as Pecan app.' % __name__)
    if not config:
        config = __get_pecan_config()

    app_conf = dict(config.app)

    active_hooks = [hooks.CorsHook()]

    if cfg.CONF.auth.enable:
        active_hooks.append(hooks.AuthHook())

    app = pecan.make_app(app_conf.pop('root'),
                         logging=getattr(config, 'logging', {}),
                         hooks=active_hooks,
                         **app_conf
                         )

    LOG.info('%s app created.' % __name__)

    return app


def get_webui_app(config=None):
    LOG.info(VERSION_STRING)
    LOG.info('Creating %s as Pecan app.' % __name__)

    opts = cfg.CONF.api_pecan
    cfg_dict = {
        'app': {
            'root': 'st2api.controllers.root.WebUIRootController',
            'static_root': '/opt/stackstorm/webui',
            'template_path': '/opt/stackstorm/webui',
            'modules': [],
            'debug': True,
            'auth_enable': False,
            'errors': opts.errors
        }
    }
    config = pecan.configuration.conf_from_dict(cfg_dict)
    app_conf = dict(config.app)

    app = pecan.make_app(logging=getattr(config, 'logging', {}),
                         **app_conf)

    LOG.info('%s app created.' % __name__)

    return app
