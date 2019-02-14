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

from tooz.coordination import GroupNotCreated

from st2common.services import coordination
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.rbac import utils as rbac_utils

__all__ = [
    'ServiceRegistryGroupsController',
    'ServiceRegistryGroupMembersController',
]


class ServiceRegistryGroupsController(object):
    def get_all(self, requester_user):
        rbac_utils.assert_user_is_admin(user_db=requester_user)

        coordinator = coordination.get_coordinator()

        group_ids = list(coordinator.get_groups().get())
        group_ids = [group_id_.decode('utf-8') for group_id_ in group_ids]

        result = {
            'groups': group_ids
        }
        return result


class ServiceRegistryGroupMembersController(object):
    def get_one(self, group_id, requester_user):
        rbac_utils.assert_user_is_admin(user_db=requester_user)

        coordinator = coordination.get_coordinator()

        try:
            member_ids = list(coordinator.get_members(group_id).get())
        except GroupNotCreated:
            msg = ('Group with ID "%s" not found.' % (group_id))
            raise StackStormDBObjectNotFoundError(msg)
        member_ids = [member_id.decode('utf-8') for member_id in member_ids]

        result = {
            'members': []
        }

        for member_id in member_ids:
            capabilities = coordinator.get_member_capabilities(group_id, member_id).get()
            item = {
                'member_id': member_id,
                'capabilities': capabilities
            }
            result['members'].append(item)

        return result

groups_controller = ServiceRegistryGroupsController()
members_controller = ServiceRegistryGroupMembersController()
