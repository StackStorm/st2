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

from oslo_config import cfg

from st2common.rbac.backends import get_rbac_backend
from st2common.services.rbac import get_roles_for_user

__all__ = [
    'UserController'
]


class UserController(object):
    def get(self, requester_user, auth_info):
        """
        Meta API endpoint wich returns information about the currently authenticated user.

            Handle:
                GET /v1/user
        """

        data = {}

        if cfg.CONF.rbac.enable and requester_user:
            role_dbs = get_roles_for_user(user_db=requester_user)
            roles = [role_db.name for role_db in role_dbs]
        else:
            roles = []

        rbac_utils = get_rbac_backend().get_utils_class()
        data = {
            'username': requester_user.name,
            'authentication': {
                'method': auth_info['method'],
                'location': auth_info['location']
            },
            'rbac': {
                'enabled': cfg.CONF.rbac.enable,
                'roles': roles,
                'is_admin': rbac_utils.user_is_admin(user_db=requester_user)
            }
        }

        if auth_info.get('token_expire', None):
            token_expire = auth_info['token_expire'].strftime('%Y-%m-%dT%H:%M:%SZ')
            data['authentication']['token_expire'] = token_expire

        return data


user_controller = UserController()
