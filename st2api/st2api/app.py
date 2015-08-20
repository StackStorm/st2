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

import pecan
from oslo_config import cfg
from pecan.middleware.static import StaticFileMiddleware

from st2common import hooks
from st2common import log as logging
from st2common.constants.system import VERSION_STRING


LOG = logging.getLogger(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def __get_pecan_config():
    opts = cfg.CONF.api_pecan

    cfg_dict = {
        'app': {
            'root': opts.root,
            'template_path': opts.template_path,
            'modules': opts.modules,
            'debug': opts.debug,
            'auth_enable': opts.auth_enable,
            'errors': opts.errors,
            'guess_content_type_from_ext': False
        }
    }

    return pecan.configuration.conf_from_dict(cfg_dict)


def setup_app(config=None):
    LOG.info(VERSION_STRING)
    LOG.info('Creating %s as Pecan app.' % __name__)

    if not config:
        config = __get_pecan_config()

    app_conf = dict(config.app)

    active_hooks = [hooks.RequestIDHook(), hooks.JSONErrorResponseHook(), hooks.LoggingHook()]

    if cfg.CONF.auth.enable:
        active_hooks.append(hooks.AuthHook())

    active_hooks.append(hooks.CorsHook())

    app = pecan.make_app(app_conf.pop('root'),
                         logging=getattr(config, 'logging', {}),
                         hooks=active_hooks,
                         **app_conf
                         )

    # Static middleware which servers common static assets such as logos
    static_root = os.path.join(BASE_DIR, 'public')
    app = StaticFileMiddleware(app=app, directory=static_root)

    LOG.info('%s app created.' % __name__)

    return app
