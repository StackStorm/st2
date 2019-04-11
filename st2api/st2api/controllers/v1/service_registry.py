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

import six

from tooz.coordination import GroupNotCreated

from st2common.services import coordination
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.rbac.backends import get_rbac_backend

__all__ = [
    'ServiceRegistryGroupsController',
    'ServiceRegistryGroupMembersController',
]


class ServiceRegistryGroupsController(object):
    def get_all(self, requester_user):
        rbac_utils = get_rbac_backend().get_utils_class()
        rbac_utils.assert_user_is_admin(user_db=requester_user)

        coordinator = coordination.get_coordinator()

        group_ids = list(coordinator.get_groups().get())
        group_ids = [item.decode('utf-8') for item in group_ids]

        result = {
            'groups': group_ids
        }
        return result


class ServiceRegistryGroupMembersController(object):
    def get_one(self, group_id, requester_user):
        rbac_utils = get_rbac_backend().get_utils_class()
        rbac_utils.assert_user_is_admin(user_db=requester_user)

        coordinator = coordination.get_coordinator()

        if not isinstance(group_id, six.binary_type):
            group_id = group_id.encode('utf-8')

        try:
            member_ids = list(coordinator.get_members(group_id).get())
        except GroupNotCreated:
            msg = ('Group with ID "%s" not found.' % (group_id.decode('utf-8')))
            raise StackStormDBObjectNotFoundError(msg)

        result = {
            'members': []
        }

        for member_id in member_ids:
            capabilities = coordinator.get_member_capabilities(group_id, member_id).get()
            item = {
                'group_id': group_id.decode('utf-8'),
                'member_id': member_id.decode('utf-8'),
                'capabilities': capabilities
            }
            result['members'].append(item)

        return result


groups_controller = ServiceRegistryGroupsController()
members_controller = ServiceRegistryGroupMembersController()
