
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


from st2common.rbac.types import PermissionType
from st2common.rbac.types import ResourceType
from st2common.persistence.auth import User
from st2common.persistence.rbac import Role
from st2common.persistence.rbac import UserRoleAssignment
from st2common.persistence.rbac import PermissionGrant
from st2common.models.db.auth import UserDB
from st2common.models.db.rbac import RoleDB
from st2common.models.db.rbac import UserRoleAssignmentDB
from st2common.models.db.rbac import PermissionGrantDB
from st2common.models.db.actionalias import ActionAliasDB
from st2common.models.api.action import ActionAliasAPI
from st2common.rbac.resolvers import ActionAliasPermissionsResolver
from tests.unit.test_rbac_resolvers import BasePermissionsResolverTestCase

__all__ = [
    'ActionAliasPermissionsResolverTestCase'
]


class ActionAliasPermissionsResolverTestCase(BasePermissionsResolverTestCase):
    def setUp(self):
        super(ActionAliasPermissionsResolverTestCase, self).setUp()

        # Create some mock users
        user_1_db = UserDB(name='alias_pack_grant')
        user_1_db = User.add_or_update(user_1_db)
        self.users['alias_pack_grant'] = user_1_db

        user_2_db = UserDB(name='alias_grant')
        user_2_db = User.add_or_update(user_2_db)
        self.users['alias_grant'] = user_2_db

        user_3_db = UserDB(name='pack_alias_all_grant')
        user_3_db = User.add_or_update(user_3_db)
        self.users['pack_alias_all_grant'] = user_3_db

        user_4_db = UserDB(name='alias_all_grant')
        user_4_db = User.add_or_update(user_4_db)
        self.users['alias_all_grant'] = user_4_db

        user_5_db = UserDB(name='alias_modify_grant')
        user_5_db = User.add_or_update(user_5_db)
        self.users['alias_modify_grant'] = user_5_db

        user_6_db = UserDB(name='alias_pack_alias_create_grant')
        user_6_db = User.add_or_update(user_6_db)
        self.users['alias_pack_alias_create_grant'] = user_6_db

        user_7_db = UserDB(name='alias_pack_alias_all_grant')
        user_7_db = User.add_or_update(user_7_db)
        self.users['alias_pack_alias_all_grant'] = user_7_db

        user_8_db = UserDB(name='alias_alias_create_grant')
        user_8_db = User.add_or_update(user_8_db)
        self.users['alias_alias_create_grant'] = user_8_db

        user_10_db = UserDB(name='alias_list_grant')
        user_10_db = User.add_or_update(user_10_db)
        self.users['alias_list_grant'] = user_10_db

        # Create some mock resources on which permissions can be granted
        alias_1_db = ActionAliasDB(pack='test_pack_1', name='alias1', formats=['a'],
                                   action_ref='core.local')
        self.resources['alias_1'] = alias_1_db

        alias_2_db = ActionAliasDB(pack='test_pack_1', name='alias2', formats=['a'],
                                   action_ref='core.local')
        self.resources['alias_2'] = alias_2_db

        alias_3_db = ActionAliasDB(pack='test_pack_2', name='alias3', formats=['a'],
                                   action_ref='core.local')
        self.resources['alias_3'] = alias_3_db

        # Create some mock roles with associated permission grants
        # One grant on parent pack, action_alias_view on pack1
        grant_db = PermissionGrantDB(resource_uid=self.resources['pack_1'].get_uid(),
                                     resource_type=ResourceType.PACK,
                                     permission_types=[PermissionType.ACTION_ALIAS_VIEW])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_3_db = RoleDB(name='alias_pack_grant',
                           permission_grants=permission_grants)
        role_3_db = Role.add_or_update(role_3_db)
        self.roles['alias_pack_grant'] = role_3_db

        # "action_alias_view" on alias_3
        grant_db = PermissionGrantDB(resource_uid=self.resources['alias_3'].get_uid(),
                                     resource_type=ResourceType.ACTION_ALIAS,
                                     permission_types=[PermissionType.ACTION_ALIAS_VIEW])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_4_db = RoleDB(name='alias_grant', permission_grants=permission_grants)
        role_4_db = Role.add_or_update(role_4_db)
        self.roles['alias_grant'] = role_4_db

        # Custom role - "action_alias_all" grant on a parent pack
        grant_db = PermissionGrantDB(resource_uid=self.resources['pack_1'].get_uid(),
                                     resource_type=ResourceType.PACK,
                                     permission_types=[PermissionType.ACTION_ALIAS_ALL])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_4_db = RoleDB(name='pack_alias_all_grant',
                           permission_grants=permission_grants)
        role_4_db = Role.add_or_update(role_4_db)
        self.roles['pack_alias_all_grant'] = role_4_db

        # Custom role - "action_alias_all" grant on alias
        grant_db = PermissionGrantDB(resource_uid=self.resources['alias_1'].get_uid(),
                                     resource_type=ResourceType.ACTION_ALIAS,
                                     permission_types=[PermissionType.ACTION_ALIAS_ALL])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_4_db = RoleDB(name='alias_all_grant', permission_grants=permission_grants)
        role_4_db = Role.add_or_update(role_4_db)
        self.roles['alias_all_grant'] = role_4_db

        # Custom role - "alias_modify" on alias_1
        grant_db = PermissionGrantDB(resource_uid=self.resources['alias_1'].get_uid(),
                                     resource_type=ResourceType.ACTION_ALIAS,
                                     permission_types=[PermissionType.ACTION_ALIAS_MODIFY])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_5_db = RoleDB(name='alias_modify_grant',
                           permission_grants=permission_grants)
        role_5_db = Role.add_or_update(role_5_db)
        self.roles['alias_modify_grant'] = role_5_db

        # Custom role - "action_alias_create" grant on pack_1
        grant_db = PermissionGrantDB(resource_uid=self.resources['pack_1'].get_uid(),
                                     resource_type=ResourceType.PACK,
                                     permission_types=[PermissionType.ACTION_ALIAS_CREATE])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_6_db = RoleDB(name='alias_pack_alias_create_grant',
                           permission_grants=permission_grants)
        role_6_db = Role.add_or_update(role_6_db)
        self.roles['alias_pack_alias_create_grant'] = role_6_db

        # Custom role - "action_alias_all" grant on pack_1
        grant_db = PermissionGrantDB(resource_uid=self.resources['pack_1'].get_uid(),
                                     resource_type=ResourceType.PACK,
                                     permission_types=[PermissionType.ACTION_ALIAS_ALL])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_7_db = RoleDB(name='alias_pack_alias_all_grant',
                           permission_grants=permission_grants)
        role_7_db = Role.add_or_update(role_7_db)
        self.roles['alias_pack_alias_all_grant'] = role_7_db

        # Custom role - "action_alias_create" grant on alias_1
        grant_db = PermissionGrantDB(resource_uid=self.resources['alias_1'].get_uid(),
                                     resource_type=ResourceType.ACTION_ALIAS,
                                     permission_types=[PermissionType.ACTION_ALIAS_CREATE])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_8_db = RoleDB(name='alias_alias_create_grant',
                           permission_grants=permission_grants)
        role_8_db = Role.add_or_update(role_8_db)
        self.roles['alias_alias_create_grant'] = role_8_db

        # Custom role - "alias_list" grant
        grant_db = PermissionGrantDB(resource_uid=None,
                                     resource_type=None,
                                     permission_types=[PermissionType.ACTION_ALIAS_LIST])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_10_db = RoleDB(name='alias_list_grant',
                           permission_grants=permission_grants)
        role_10_db = Role.add_or_update(role_10_db)
        self.roles['alias_list_grant'] = role_10_db

        # Create some mock role assignments
        user_db = self.users['alias_pack_grant']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['alias_pack_grant'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        user_db = self.users['alias_grant']
        role_assignment_db = UserRoleAssignmentDB(user=user_db.name,
                                                  role=self.roles['alias_grant'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        user_db = self.users['pack_alias_all_grant']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['pack_alias_all_grant'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        user_db = self.users['alias_all_grant']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['alias_all_grant'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        user_db = self.users['alias_modify_grant']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['alias_modify_grant'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        user_db = self.users['alias_pack_alias_create_grant']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['alias_pack_alias_create_grant'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        user_db = self.users['alias_pack_alias_all_grant']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['alias_pack_alias_all_grant'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        user_db = self.users['alias_alias_create_grant']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['alias_alias_create_grant'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        user_db = self.users['alias_list_grant']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['alias_list_grant'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

    def test_user_has_permission(self):
        resolver = ActionAliasPermissionsResolver()

        # Admin user, should always return true
        user_db = self.users['admin']
        self.assertUserHasPermission(resolver=resolver,
                                     user_db=user_db,
                                     permission_type=PermissionType.ACTION_ALIAS_LIST)

        # Observer, should always return true for VIEW permissions
        user_db = self.users['observer']
        self.assertUserHasPermission(resolver=resolver,
                                     user_db=user_db,
                                     permission_type=PermissionType.ACTION_ALIAS_LIST)

        # No roles, should return false for everything
        user_db = self.users['no_roles']
        self.assertUserDoesntHavePermission(resolver=resolver,
                                            user_db=user_db,
                                            permission_type=PermissionType.ACTION_ALIAS_LIST)

        # Custom role with no permission grants, should return false for everything
        user_db = self.users['1_custom_role_no_permissions']
        self.assertUserDoesntHavePermission(resolver=resolver,
                                            user_db=user_db,
                                            permission_type=PermissionType.ACTION_ALIAS_LIST)

        # Custom role with "action_list" grant
        user_db = self.users['alias_list_grant']
        self.assertUserHasPermission(resolver=resolver,
                                     user_db=user_db,
                                     permission_type=PermissionType.ACTION_ALIAS_LIST)

    def test_user_has_resource_api_permission(self):
        resolver = ActionAliasPermissionsResolver()

        # Admin user, should always return true
        user_db = self.users['admin']
        resource_db = self.resources['alias_1']
        resource_api = ActionAliasAPI.from_model(resource_db)

        self.assertUserHasResourceApiPermission(
            resolver=resolver,
            user_db=user_db,
            resource_api=resource_api,
            permission_type=PermissionType.ACTION_ALIAS_CREATE)

        # Observer, should return false
        user_db = self.users['observer']
        resource_db = self.resources['alias_1']
        resource_api = ActionAliasAPI.from_model(resource_db)

        self.assertUserDoesntHaveResourceApiPermission(
            resolver=resolver,
            user_db=user_db,
            resource_api=resource_api,
            permission_type=PermissionType.ACTION_ALIAS_CREATE)

        # No roles, should return false
        user_db = self.users['no_roles']
        resource_db = self.resources['alias_1']
        resource_api = ActionAliasAPI.from_model(resource_db)

        self.assertUserDoesntHaveResourceApiPermission(
            resolver=resolver,
            user_db=user_db,
            resource_api=resource_api,
            permission_type=PermissionType.ACTION_ALIAS_CREATE)

        # Custom role with no permission grants, should return false
        user_db = self.users['1_custom_role_no_permissions']
        resource_db = self.resources['alias_1']
        resource_api = ActionAliasAPI.from_model(resource_db)

        self.assertUserDoesntHaveResourceApiPermission(
            resolver=resolver,
            user_db=user_db,
            resource_api=resource_api,
            permission_type=PermissionType.ACTION_ALIAS_CREATE)

        # Custom role with "action_alias_create" grant on parent pack
        user_db = self.users['alias_pack_alias_create_grant']
        resource_db = self.resources['alias_1']
        resource_api = ActionAliasAPI.from_model(resource_db)

        self.assertUserHasResourceApiPermission(
            resolver=resolver,
            user_db=user_db,
            resource_api=resource_api,
            permission_type=PermissionType.ACTION_ALIAS_CREATE)

        # Custom role with "action_alias_all" grant on the parent pack
        user_db = self.users['alias_pack_alias_all_grant']
        resource_db = self.resources['alias_1']
        resource_api = ActionAliasAPI.from_model(resource_db)

        self.assertUserHasResourceApiPermission(
            resolver=resolver,
            user_db=user_db,
            resource_api=resource_api,
            permission_type=PermissionType.ACTION_ALIAS_CREATE)

        # Custom role with "action_alias_create" grant directly on the resource
        user_db = self.users['alias_alias_create_grant']
        resource_db = self.resources['alias_1']
        resource_api = ActionAliasAPI.from_model(resource_db)

        self.assertUserHasResourceApiPermission(
            resolver=resolver,
            user_db=user_db,
            resource_api=resource_api,
            permission_type=PermissionType.ACTION_ALIAS_CREATE)

        # Custom role with "action_alias_all" grant directly on the resource
        user_db = self.users['alias_all_grant']
        resource_db = self.resources['alias_1']
        resource_api = ActionAliasAPI.from_model(resource_db)

        self.assertUserHasResourceApiPermission(
            resolver=resolver,
            user_db=user_db,
            resource_api=resource_api,
            permission_type=PermissionType.ACTION_ALIAS_CREATE)

    def test_user_has_resource_db_permission(self):
        resolver = ActionAliasPermissionsResolver()
        all_permission_types = PermissionType.get_valid_permissions_for_resource_type(
            ResourceType.ACTION_ALIAS)

        # Admin user, should always return true
        resource_db = self.resources['alias_1']
        user_db = self.users['admin']

        self.assertUserHasResourceDbPermissions(
            resolver=resolver,
            user_db=user_db,
            resource_db=resource_db,
            permission_types=all_permission_types)

        # Observer, should always return true for VIEW permission
        user_db = self.users['observer']
        self.assertUserHasResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=self.resources['alias_1'],
            permission_type=PermissionType.ACTION_ALIAS_VIEW)
        self.assertUserHasResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=self.resources['alias_2'],
            permission_type=PermissionType.ACTION_ALIAS_VIEW)

        self.assertUserDoesntHaveResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=self.resources['alias_1'],
            permission_type=PermissionType.ACTION_ALIAS_MODIFY)
        self.assertUserDoesntHaveResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=self.resources['alias_2'],
            permission_type=PermissionType.ACTION_ALIAS_DELETE)

        # No roles, should return false for everything
        user_db = self.users['no_roles']
        self.assertUserDoesntHaveResourceDbPermissions(
            resolver=resolver,
            user_db=user_db,
            resource_db=resource_db,
            permission_types=all_permission_types)

        # Custom role with no permission grants, should return false for everything
        user_db = self.users['1_custom_role_no_permissions']
        self.assertUserDoesntHaveResourceDbPermissions(
            resolver=resolver,
            user_db=user_db,
            resource_db=resource_db,
            permission_types=all_permission_types)

        # Custom role with unrelated permission grant to parent pack
        user_db = self.users['alias_pack_grant']
        self.assertUserDoesntHaveResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=self.resources['alias_1'],
            permission_type=PermissionType.ACTION_ALIAS_DELETE)
        self.assertUserDoesntHaveResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=self.resources['alias_1'],
            permission_type=PermissionType.ACTION_ALIAS_MODIFY)

        # Custom role with with grant on the parent pack
        user_db = self.users['alias_pack_grant']
        self.assertUserHasResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=self.resources['alias_1'],
            permission_type=PermissionType.ACTION_ALIAS_VIEW)
        self.assertUserHasResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=self.resources['alias_2'],
            permission_type=PermissionType.ACTION_ALIAS_VIEW)

        self.assertUserDoesntHaveResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=self.resources['alias_2'],
            permission_type=PermissionType.ACTION_ALIAS_DELETE)

        # Custom role with a direct grant on alias
        user_db = self.users['alias_grant']
        self.assertUserHasResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=self.resources['alias_3'],
            permission_type=PermissionType.ACTION_ALIAS_VIEW)

        self.assertUserDoesntHaveResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=self.resources['alias_2'],
            permission_type=PermissionType.ACTION_ALIAS_MODIFY)
        self.assertUserDoesntHaveResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=self.resources['alias_3'],
            permission_type=PermissionType.ACTION_ALIAS_MODIFY)

        # Custom role - "action_alias_all" grant on the parent pack
        user_db = self.users['pack_alias_all_grant']
        resource_db = self.resources['alias_1']
        self.assertUserHasResourceDbPermissions(
            resolver=resolver,
            user_db=user_db,
            resource_db=resource_db,
            permission_types=all_permission_types)

        # Custom role - "action_alias_all" grant on the alias
        user_db = self.users['alias_all_grant']
        resource_db = self.resources['alias_1']
        self.assertUserHasResourceDbPermissions(
            resolver=resolver,
            user_db=user_db,
            resource_db=resource_db,
            permission_types=all_permission_types)

        # Custom role - "action_alias_modify" grant on alias_1
        user_db = self.users['alias_modify_grant']
        resource_db = self.resources['alias_1']
        self.assertUserHasResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=resource_db,
            permission_type=PermissionType.ACTION_ALIAS_MODIFY)

        # "modify" also grants "view"
        self.assertUserHasResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=resource_db,
            permission_type=PermissionType.ACTION_ALIAS_VIEW)

        permission_types = [
            PermissionType.ACTION_ALIAS_CREATE,
            PermissionType.ACTION_ALIAS_DELETE
        ]
        self.assertUserDoesntHaveResourceDbPermissions(
            resolver=resolver,
            user_db=user_db,
            resource_db=resource_db,
            permission_types=permission_types)
