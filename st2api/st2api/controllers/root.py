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

from pecan import expose

from st2common import __version__
from st2common import log as logging
from st2common.controllers import BaseRootController
import st2api.controllers.exp.root as exp_root
import st2api.controllers.v1.root as v1_root

__all__ = [
    'RootController'
]

LOG = logging.getLogger(__name__)


class RootController(BaseRootController):
    logger = LOG

    def __init__(self):
        v1_controller = v1_root.RootController()
        exp_controller = exp_root.RootController()

        self.controllers = {
            'v1': v1_controller,
            'exp': exp_controller
        }

        self.default_controller = v1_controller

    @expose(generic=True, template='index.html')
    def index(self):
        data = {}

        if 'dev' in __version__:
            docs_url = 'http://docs.stackstorm.com/latest'
        else:
            docs_version = '.'.join(__version__.split('.')[:2])
            docs_url = 'http://docs.stackstorm.com/%s' % docs_version

        data['version'] = __version__
        data['docs_url'] = docs_url
        return data
