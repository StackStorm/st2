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

__all__ = [
    'RootController'
]

from oslo_config import cfg

from st2common import __version__
from st2common.services.rbac import get_roles_for_user


class RootController(object):
    def index(self, requester_user=None):
        data = {}

        if 'dev' in __version__:
            docs_url = 'http://docs.stackstorm.com/latest'
        else:
            docs_version = '.'.join(__version__.split('.')[:2])
            docs_url = 'http://docs.stackstorm.com/%s' % docs_version

        if requester_user:
            authenticated_user = requester_user.name
        else:
            authenticated_user = 'None'

        if cfg.CONF.rbac.enable and requester_user:
            role_dbs = get_roles_for_user(user_db=requester_user)
            roles = [role_db.name for role_db in role_dbs]
        else:
            roles = []

        data['version'] = __version__
        data['docs_url'] = docs_url
        data['user'] = {
            'authenticated': True if requester_user else None,
            'username': authenticated_user,
            'rbac': {
                'enabled': cfg.CONF.rbac.enable,
                'roles': roles
            },
        }
        return data


root_controller = RootController()
