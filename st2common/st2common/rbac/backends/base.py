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

import abc

import six


__all__ = [
    'BaseRBACBackend',
    'BaseRBACPermissionResolver',
    'BaseRBACRemoteGroupToRoleSyncer'
]


@six.add_metaclass(abc.ABCMeta)
class BaseRBACBackend(object):
    def get_resolver_for_resource_type(resource_type):
        """
        Method which returns PermissionResolver class for the provided resource type.
        """
        raise NotImplementedError()

    def get_resolver_for_permission_type(resource_type):
        """
        Method which returns PermissionResolver class for the provided permission type.
        """
        raise NotImplementedError()

    def get_remote_group_to_role_syncer(self):
        """
        Return instance of RBACRemoteGroupToRoleSyncer class.
        """
        raise NotImplementedError()


@six.add_metaclass(abc.ABCMeta)
class BaseRBACPermissionResolver(object):

    def user_has_permission(self, user_db, permission_type):
        """
        Method for checking user permissions which are not tied to a particular resource.
        """
        raise NotImplementedError()

    def user_has_resource_api_permission(self, user_db, resource_api, permission_type):
        """
        Method for checking user permissions on a resource which is to be created (e.g.
        create operation).
        """
        raise NotImplementedError()

    def user_has_resource_db_permission(self, user_db, resource_db, permission_type):
        """
        Method for checking user permissions on an existing resource (e.g. get one, edit, delete
        operations).
        """
        raise NotImplementedError()


@six.add_metaclass(abc.ABCMeta)
class BaseRBACRemoteGroupToRoleSyncer(object):
    def sync(self, user_db, groups):
        """
        :param user_db: User to sync the assignments for.
        :type user: :class:`UserDB`

        :param groups: A list of remote groups user is a member of.
        :type groups: ``list`` of ``str``

        :return: A list of mappings which have been created.
        :rtype: ``list`` of :class:`UserRoleAssignmentDB`
        """
        raise NotImplementedError()
