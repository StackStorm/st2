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

from st2common import hooks
from st2common import log as logging


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

    if not config:
        config = _get_pecan_config()

    app_conf = dict(config.app)

    return pecan.make_app(
        app_conf.pop('root'),
        logging=getattr(config, 'logging', {}),
        hooks=[hooks.JSONErrorResponseHook(), hooks.CorsHook()],
        **app_conf
    )
