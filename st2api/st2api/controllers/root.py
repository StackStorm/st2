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

from pecan import expose
from pecan.core import redirect
from oslo.config import cfg

from st2common import __version__
from st2common import log as logging
import st2api.controllers.v1.root as v1_root
import st2api.controllers.exp.root as exp_root

__all__ = [
    'WebUIRootController',
    'RootController'
]

LOG = logging.getLogger(__name__)


class WebUIRootController(object):
    @expose(generic=True)
    def index(self):
        webui_root = os.path.join(cfg.CONF.api_pecan.static_root, 'webui')
        webui_index_file = os.path.join(webui_root, 'index.html')

        if not os.path.exists(webui_index_file):
            message = 'Cannot find WebUI files. Make sure they are located in %s.' % (webui_root)
            return message

        return redirect(location='/webui/index.html')


class RootController(object):

    def __init__(self):
        v1_controller = v1_root.RootController()
        exp_controller = exp_root.RootController()
        self.controllers = {
            'v1': v1_controller,
            'exp': exp_controller
        }

        if cfg.CONF.api.serve_webui_files:
            webui_controller = WebUIRootController()
            self.controllers['webui'] = webui_controller

        self.default_controller = v1_controller

    @expose(generic=True, template='index.html')
    def index(self):
        data = {}

        if 'dev' in __version__:
            docs_url = 'http://docs.stackstorm.com/latest'
        else:
            docs_url = 'http://docs.stackstorm.com/%s' % (__version__)

        data['version'] = __version__
        data['docs_url'] = docs_url
        data['webui_enabled'] = cfg.CONF.api.serve_webui_files
        return data

    @expose()
    def _lookup(self, *remainder):
        version = ''
        if len(remainder) > 0:
            version = remainder[0]
            if cfg.CONF.api.serve_webui_files and version == 'webui':
                # Special case for handling webui requests
                return self.controllers['webui'], remainder[1:]

            if remainder[len(remainder) - 1] == '':
                # If the url has a trailing '/' remainder will contain an empty string.
                # In order for further pecan routing to work this method needs to remove
                # the empty string from end of the tuple.
                remainder = remainder[:len(remainder) - 1]
        versioned_controller = self.controllers.get(version, None)
        if versioned_controller:
            return versioned_controller, remainder[1:]
        LOG.debug('No version specified in URL. Will use default controller.')
        return self.default_controller, remainder
