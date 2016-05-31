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

from st2common.constants import action as action_constants
from st2common.rbac.types import PermissionType
from st2common.rbac.types import ResourceType
from st2common.persistence.auth import User
from st2common.persistence.rbac import Role
from st2common.persistence.rbac import UserRoleAssignment
from st2common.persistence.rbac import PermissionGrant
from st2common.persistence.action import Action
from st2common.persistence.execution import ActionExecution
from st2common.models.db.auth import UserDB
from st2common.models.db.rbac import RoleDB
from st2common.models.db.rbac import UserRoleAssignmentDB
from st2common.models.db.rbac import PermissionGrantDB
from st2common.models.db.action import ActionDB
from st2common.models.db.execution import ActionExecutionDB
from st2common.rbac.resolvers import ExecutionPermissionsResolver
from tests.unit.test_rbac_resolvers import BasePermissionsResolverTestCase

__all__ = [
    'ExecutionPermissionsResolverTestCase'
]


class ExecutionPermissionsResolverTestCase(BasePermissionsResolverTestCase):
    def setUp(self):
        super(ExecutionPermissionsResolverTestCase, self).setUp()

        # Create some mock users
        user_1_db = UserDB(name='custom_role_unrelated_pack_action_grant')
        user_1_db = User.add_or_update(user_1_db)
        self.users['custom_role_unrelated_pack_action_grant'] = user_1_db

        user_2_db = UserDB(name='custom_role_pack_action_grant_unrelated_permission')
        user_2_db = User.add_or_update(user_2_db)
        self.users['custom_role_pack_action_grant_unrelated_permission'] = user_2_db

        user_3_db = UserDB(name='custom_role_pack_action_view_grant')
        user_3_db = User.add_or_update(user_3_db)
        self.users['custom_role_pack_action_view_grant'] = user_3_db

        user_4_db = UserDB(name='custom_role_action_view_grant')
        user_4_db = User.add_or_update(user_4_db)
        self.users['custom_role_action_view_grant'] = user_4_db

        user_5_db = UserDB(name='custom_role_pack_action_execute_grant')
        user_5_db = User.add_or_update(user_5_db)
        self.users['custom_role_pack_action_execute_grant'] = user_5_db

        user_6_db = UserDB(name='custom_role_action_execute_grant')
        user_6_db = User.add_or_update(user_6_db)
        self.users['custom_role_action_execute_grant'] = user_6_db

        user_7_db = UserDB(name='custom_role_pack_action_all_grant')
        user_7_db = User.add_or_update(user_7_db)
        self.users['custom_role_pack_action_all_grant'] = user_7_db

        user_8_db = UserDB(name='custom_role_action_all_grant')
        user_8_db = User.add_or_update(user_8_db)
        self.users['custom_role_action_all_grant'] = user_8_db

        user_9_db = UserDB(name='custom_role_execution_list_grant')
        user_9_db = User.add_or_update(user_5_db)
        self.users['custom_role_execution_list_grant'] = user_9_db

        # Create some mock resources on which permissions can be granted
        action_1_db = ActionDB(pack='test_pack_2', name='action1', entry_point='',
                               runner_type={'name': 'run-local'})
        action_1_db = Action.add_or_update(action_1_db)
        self.resources['action_1'] = action_1_db

        runner = {'name': 'run-python'}
        liveaction = {'action': 'test_pack_2.action1'}
        status = action_constants.LIVEACTION_STATUS_REQUESTED

        action = {'uid': action_1_db.get_uid(), 'pack': 'test_pack_2'}
        exec_1_db = ActionExecutionDB(action=action, runner=runner, liveaction=liveaction,
                                      status=status)
        exec_1_db = ActionExecution.add_or_update(exec_1_db)
        self.resources['exec_1'] = exec_1_db

        # Create some mock roles with associated permission grants
        # Custom role - one grant to an unrelated pack
        grant_db = PermissionGrantDB(resource_uid=self.resources['pack_1'].get_uid(),
                                     resource_type=ResourceType.PACK,
                                     permission_types=[PermissionType.ACTION_VIEW])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_db = RoleDB(name='custom_role_unrelated_pack_action_grant',
                         permission_grants=permission_grants)
        role_db = Role.add_or_update(role_db)
        self.roles['custom_role_unrelated_pack_action_grant'] = role_db

        # Custom role - one grant of unrelated permission type to parent action pack
        grant_db = PermissionGrantDB(resource_uid=self.resources['pack_2'].get_uid(),
                                     resource_type=ResourceType.PACK,
                                     permission_types=[PermissionType.RULE_VIEW])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_db = RoleDB(name='custom_role_pack_action_grant_unrelated_permission',
                         permission_grants=permission_grants)
        role_db = Role.add_or_update(role_db)
        self.roles['custom_role_pack_action_grant_unrelated_permission'] = role_db

        # Custom role - one grant of "action_view" to the parent pack of the action the execution
        # belongs to
        grant_db = PermissionGrantDB(resource_uid=self.resources['pack_2'].get_uid(),
                                     resource_type=ResourceType.PACK,
                                     permission_types=[PermissionType.ACTION_VIEW])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_db = RoleDB(name='custom_role_pack_action_view_grant',
                         permission_grants=permission_grants)
        role_db = Role.add_or_update(role_db)
        self.roles['custom_role_pack_action_view_grant'] = role_db

        # Custom role - one grant of "action_view" to the action the execution belongs to
        grant_db = PermissionGrantDB(resource_uid=self.resources['action_1'].get_uid(),
                                     resource_type=ResourceType.ACTION,
                                     permission_types=[PermissionType.ACTION_VIEW])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_db = RoleDB(name='custom_role_action_view_grant',
                         permission_grants=permission_grants)
        role_db = Role.add_or_update(role_db)
        self.roles['custom_role_action_view_grant'] = role_db

        # Custom role - one grant of "action_execute" to the parent pack of the action the
        # execution belongs to
        grant_db = PermissionGrantDB(resource_uid=self.resources['pack_2'].get_uid(),
                                     resource_type=ResourceType.PACK,
                                     permission_types=[PermissionType.ACTION_EXECUTE])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_db = RoleDB(name='custom_role_pack_action_execute_grant',
                         permission_grants=permission_grants)
        role_db = Role.add_or_update(role_db)
        self.roles['custom_role_pack_action_execute_grant'] = role_db

        # Custom role - one grant of "action_execute" to the the action the execution belongs to
        grant_db = PermissionGrantDB(resource_uid=self.resources['action_1'].get_uid(),
                                     resource_type=ResourceType.ACTION,
                                     permission_types=[PermissionType.ACTION_EXECUTE])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_db = RoleDB(name='custom_role_action_execute_grant',
                         permission_grants=permission_grants)
        role_db = Role.add_or_update(role_db)
        self.roles['custom_role_action_execute_grant'] = role_db

        # Custom role - "action_all" grant on a parent action pack the execution belongs to
        grant_db = PermissionGrantDB(resource_uid=self.resources['pack_2'].get_uid(),
                                     resource_type=ResourceType.PACK,
                                     permission_types=[PermissionType.ACTION_ALL])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_4_db = RoleDB(name='custom_role_pack_action_all_grant',
                           permission_grants=permission_grants)
        role_4_db = Role.add_or_update(role_4_db)
        self.roles['custom_role_pack_action_all_grant'] = role_4_db

        # Custom role - "action_all" grant on action the execution belongs to
        grant_db = PermissionGrantDB(resource_uid=self.resources['action_1'].get_uid(),
                                     resource_type=ResourceType.ACTION,
                                     permission_types=[PermissionType.ACTION_ALL])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_4_db = RoleDB(name='custom_role_action_all_grant',
                           permission_grants=permission_grants)
        role_4_db = Role.add_or_update(role_4_db)
        self.roles['custom_role_action_all_grant'] = role_4_db

        # Custom role - "execution_list" grant
        grant_db = PermissionGrantDB(resource_uid=None,
                                     resource_type=None,
                                     permission_types=[PermissionType.EXECUTION_LIST])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_5_db = RoleDB(name='custom_role_execution_list_grant',
                           permission_grants=permission_grants)
        role_5_db = Role.add_or_update(role_5_db)
        self.roles['custom_role_execution_list_grant'] = role_5_db

        # Create some mock role assignments
        user_db = self.users['custom_role_unrelated_pack_action_grant']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['custom_role_unrelated_pack_action_grant'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        user_db = self.users['custom_role_pack_action_grant_unrelated_permission']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['custom_role_pack_action_grant_unrelated_permission'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        user_db = self.users['custom_role_pack_action_view_grant']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['custom_role_pack_action_view_grant'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        user_db = self.users['custom_role_action_view_grant']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['custom_role_action_view_grant'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        user_db = self.users['custom_role_pack_action_execute_grant']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['custom_role_pack_action_execute_grant'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        user_db = self.users['custom_role_action_execute_grant']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['custom_role_action_execute_grant'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        user_db = self.users['custom_role_pack_action_all_grant']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['custom_role_pack_action_all_grant'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        user_db = self.users['custom_role_action_all_grant']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['custom_role_action_all_grant'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        user_db = self.users['custom_role_execution_list_grant']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['custom_role_execution_list_grant'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

    def test_user_has_permission(self):
        resolver = ExecutionPermissionsResolver()

        # Admin user, should always return true
        user_db = self.users['admin']
        self.assertUserHasPermission(resolver=resolver,
                                     user_db=user_db,
                                     permission_type=PermissionType.EXECUTION_LIST)

        # Observer, should always return true for VIEW permissions
        user_db = self.users['observer']
        self.assertUserHasPermission(resolver=resolver,
                                     user_db=user_db,
                                     permission_type=PermissionType.EXECUTION_LIST)

        # No roles, should return false for everything
        user_db = self.users['no_roles']
        self.assertUserDoesntHavePermission(resolver=resolver,
                                            user_db=user_db,
                                            permission_type=PermissionType.EXECUTION_LIST)

        # Custom role with no permission grants, should return false for everything
        user_db = self.users['1_custom_role_no_permissions']
        self.assertUserDoesntHavePermission(resolver=resolver,
                                            user_db=user_db,
                                            permission_type=PermissionType.EXECUTION_LIST)

        # Custom role with "execution_list" grant
        user_db = self.users['custom_role_execution_list_grant']
        self.assertUserHasPermission(resolver=resolver,
                                     user_db=user_db,
                                     permission_type=PermissionType.EXECUTION_LIST)

    def test_user_has_resource_db_permission(self):
        resolver = ExecutionPermissionsResolver()
        all_permission_types = PermissionType.get_valid_permissions_for_resource_type(
            ResourceType.EXECUTION)
        all_permission_types.remove(PermissionType.EXECUTION_LIST)

        # Admin user, should always return true
        resource_db = self.resources['exec_1']
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
            resource_db=self.resources['exec_1'],
            permission_type=PermissionType.EXECUTION_VIEW)

        self.assertUserDoesntHaveResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=self.resources['exec_1'],
            permission_type=PermissionType.EXECUTION_STOP)
        self.assertUserDoesntHaveResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=self.resources['exec_1'],
            permission_type=PermissionType.EXECUTION_ALL)

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

        # Custom role with an action_view grant on unrelated pack, should return false for
        # everything
        user_db = self.users['custom_role_unrelated_pack_action_grant']
        self.assertUserDoesntHaveResourceDbPermissions(
            resolver=resolver,
            user_db=user_db,
            resource_db=resource_db,
            permission_types=all_permission_types)

        # Custom role with unrelated permission grant to parent pack, should return false for
        # everything
        user_db = self.users['custom_role_pack_action_grant_unrelated_permission']
        self.assertUserDoesntHaveResourceDbPermissions(
            resolver=resolver,
            user_db=user_db,
            resource_db=resource_db,
            permission_types=all_permission_types)

        # Custom role with "action_view" grant on the pack of the action resource belongs to
        user_db = self.users['custom_role_pack_action_view_grant']
        self.assertUserHasResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=resource_db,
            permission_type=PermissionType.EXECUTION_VIEW
        )

        self.assertUserDoesntHaveResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=resource_db,
            permission_type=PermissionType.EXECUTION_RE_RUN
        )

        # Custom role with "action_view" grant on the action the resource belongs to
        user_db = self.users['custom_role_action_view_grant']
        self.assertUserHasResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=resource_db,
            permission_type=PermissionType.EXECUTION_VIEW
        )

        self.assertUserDoesntHaveResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=resource_db,
            permission_type=PermissionType.EXECUTION_RE_RUN
        )

        # Custom role with "action_execute" grant on the pack of the action resource belongs to
        user_db = self.users['custom_role_pack_action_execute_grant']
        permission_types = [PermissionType.EXECUTION_RE_RUN, PermissionType.EXECUTION_STOP]
        self.assertUserHasResourceDbPermissions(
            resolver=resolver,
            user_db=user_db,
            resource_db=resource_db,
            permission_types=permission_types)

        permission_types = [PermissionType.EXECUTION_VIEW, PermissionType.EXECUTION_ALL]
        self.assertUserDoesntHaveResourceDbPermissions(
            resolver=resolver,
            user_db=user_db,
            resource_db=resource_db,
            permission_types=permission_types)

        # Custom role with "action_execute" grant on the action resource belongs to
        user_db = self.users['custom_role_action_execute_grant']
        permission_types = [PermissionType.EXECUTION_RE_RUN, PermissionType.EXECUTION_STOP]
        self.assertUserHasResourceDbPermissions(
            resolver=resolver,
            user_db=user_db,
            resource_db=resource_db,
            permission_types=permission_types)

        permission_types = [PermissionType.EXECUTION_VIEW, PermissionType.EXECUTION_ALL]
        self.assertUserDoesntHaveResourceDbPermissions(
            resolver=resolver,
            user_db=user_db,
            resource_db=resource_db,
            permission_types=permission_types)

        # Custom role - "action_all" grant on the action parent pack the execution belongs to
        user_db = self.users['custom_role_pack_action_all_grant']
        resource_db = self.resources['exec_1']
        self.assertUserHasResourceDbPermissions(
            resolver=resolver,
            user_db=user_db,
            resource_db=resource_db,
            permission_types=all_permission_types)

        # Custom role - "action_all" grant on the action the execution belongs to
        user_db = self.users['custom_role_action_all_grant']
        resource_db = self.resources['exec_1']
        self.assertUserHasResourceDbPermissions(
            resolver=resolver,
            user_db=user_db,
            resource_db=resource_db,
            permission_types=all_permission_types)
