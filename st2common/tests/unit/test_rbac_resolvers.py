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

from st2common.services import rbac as rbac_services
from st2common.rbac.types import PermissionType
from st2common.rbac.types import SystemRole
from st2common.persistence.auth import User
from st2common.persistence.rbac import Role
from st2common.persistence.rbac import UserRoleAssignment
from st2common.persistence.rbac import PermissionGrant
from st2common.persistence.pack import Pack
from st2common.persistence.action import Action
from st2common.persistence.rule import Rule
from st2common.models.db.auth import UserDB
from st2common.models.db.rbac import RoleDB
from st2common.models.db.rbac import UserRoleAssignmentDB
from st2common.models.db.rbac import PermissionGrantDB
from st2common.models.db.pack import PackDB
from st2common.models.db.action import ActionDB
from st2common.models.db.rule import RuleDB
from st2common.models.db.runner import RunnerTypeDB
from st2common.rbac.resolvers import ActionPermissionsResolver
from st2common.rbac.migrations import insert_system_roles
from st2tests.base import CleanDbTestCase


class ActionPermissionsResolverTestCase(CleanDbTestCase):
    def setUp(self):
        super(ActionPermissionsResolverTestCase, self).setUp()

        insert_system_roles()

        # Make sure RBAC is enabeld
        cfg.CONF.set_override(name='enable', override=True, group='rbac')

        # TODO: Share mocks
        self.users = {}
        self.roles = {}
        self.resources = {}

        # Create some mock users
        user_1_db = UserDB(name='admin')
        user_1_db = User.add_or_update(user_1_db)
        self.users['admin'] = user_1_db

        user_2_db = UserDB(name='observer')
        user_2_db = User.add_or_update(user_2_db)
        self.users['observer'] = user_2_db

        user_3_db = UserDB(name='no_roles')
        user_3_db = User.add_or_update(user_3_db)
        self.users['no_roles'] = user_3_db

        user_4_db = UserDB(name='1_custom_role_no_permissions')
        user_4_db = User.add_or_update(user_4_db)
        self.users['1_custom_role_no_permissions'] = user_4_db

        user_5_db = UserDB(name='1_role_pack_grant')
        user_5_db = User.add_or_update(user_5_db)
        self.users['custom_role_pack_grant'] = user_5_db

        user_6_db = UserDB(name='1_role_action_grant')
        user_6_db = User.add_or_update(user_5_db)
        self.users['custom_role_action_grant'] = user_6_db

        # Create some mock resources on which permissions can be granted
        pack_1_db = PackDB(name='test_pack_1', ref='test_pack_1', description='',
                           version='0.1.0', author='foo', email='test@example.com')
        pack_1_db = Pack.add_or_update(pack_1_db)
        self.resources['pack_1'] = pack_1_db

        action_1_db = ActionDB(pack='test_pack_1', name='action1', entry_point='',
                runner_type={'name': 'run-local'})
        action_1_db = Action.add_or_update(action_1_db)
        self.resources['action_1'] = action_1_db

        # Create some permission grants
        grant_db = PermissionGrantDB(resource_uid=self.resources['pack_1'].get_uid(),
                                     resource_type='pack',
                                     permission_types=[PermissionType.PACK_CREATE])
        grant_db = PermissionGrant.add_or_update(grant_db)
        pack_grant_dbs = [str(grant_db.id)]

        # Create some mock roles
        admin_role_db = rbac_services.get_role_by_name(name=SystemRole.ADMIN)
        observer_role_db = rbac_services.get_role_by_name(name=SystemRole.OBSERVER)
        role_1_db = rbac_services.create_role(name='custom_role_1')
        role_2_db = rbac_services.create_role(name='custom_role_2',
                                              description='custom role 2')
        role_3_db = RoleDB(name='custom_role_pack_grant', permission_grants=pack_grant_dbs)
        role_3_db = Role.add_or_update(role_3_db)
        self.roles['admin_role'] = admin_role_db
        self.roles['observer_role'] = observer_role_db
        self.roles['custom_role_1'] = role_1_db
        self.roles['custom_role_2'] = role_2_db
        self.roles['custom_role_pack_grant'] = role_3_db

        # Create some mock role assignments
        role_assignment_admin = UserRoleAssignmentDB(user=self.users['admin'].name,
                                                     role=self.roles['admin_role'].name)
        role_assignment_admin = UserRoleAssignment.add_or_update(role_assignment_admin)
        role_assignment_observer = UserRoleAssignmentDB(user=self.users['observer'].name,
                                                     role=self.roles['observer_role'].name)
        role_assignment_observer = UserRoleAssignment.add_or_update(role_assignment_observer)

        user_db = self.users['1_custom_role_no_permissions']
        role_assignment_db = UserRoleAssignmentDB(user=user_db.name,
                                                 role=self.roles['custom_role_1'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        user_db = self.users['custom_role_pack_grant']
        role_assignment_db = UserRoleAssignmentDB(user=user_db.name,
                                                 role=self.roles['custom_role_pack_grant'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

    def test_user_has_permission(self):
        resolver = ActionPermissionsResolver()

        # Admin user, should always return true
        user_db = self.users['admin']
        self.assertTrue(resolver.user_has_permission(user_db=user_db,
            permission_type=PermissionType.ACTION_CREATE))
        self.assertTrue(resolver.user_has_permission(user_db=user_db,
            permission_type=PermissionType.ACTION_EXECUTE))
        self.assertTrue(resolver.user_has_permission(user_db=user_db,
            permission_type=PermissionType.RULE_DELETE))

        # Observer, should always return true for VIEW permission
        user_db = self.users['observer']
        self.assertTrue(resolver.user_has_permission(user_db=user_db,
            permission_type=PermissionType.PACK_VIEW))
        self.assertTrue(resolver.user_has_permission(user_db=user_db,
            permission_type=PermissionType.ACTION_VIEW))
        self.assertTrue(resolver.user_has_permission(user_db=user_db,
            permission_type=PermissionType.RULE_VIEW))

        self.assertFalse(resolver.user_has_permission(user_db=user_db,
            permission_type=PermissionType.PACK_CREATE))
        self.assertFalse(resolver.user_has_permission(user_db=user_db,
            permission_type=PermissionType.ACTION_MODIFY))
        self.assertFalse(resolver.user_has_permission(user_db=user_db,
            permission_type=PermissionType.RULE_DELETE))

        # No roles, should return false
        user_db = self.users['no_roles']
        self.assertFalse(resolver.user_has_permission(user_db=user_db,
            permission_type=PermissionType.PACK_VIEW))
        self.assertFalse(resolver.user_has_permission(user_db=user_db,
            permission_type=PermissionType.ACTION_MODIFY))
        self.assertFalse(resolver.user_has_permission(user_db=user_db,
            permission_type=PermissionType.RULE_DELETE))

        # Custom role with no permissions, should return false
        user_db = self.users['1_custom_role_no_permissions']
        self.assertFalse(resolver.user_has_permission(user_db=user_db,
            permission_type=PermissionType.PACK_VIEW))
        self.assertFalse(resolver.user_has_permission(user_db=user_db,
            permission_type=PermissionType.ACTION_MODIFY))
        self.assertFalse(resolver.user_has_permission(user_db=user_db,
            permission_type=PermissionType.RULE_DELETE))

        # Custom role with permission on pack to which the action belongs to
        user_db = self.users['custom_role_pack_grant']

        self.assertTrue(resolver.user_has_permission(user_db=user_db,
            permission_type=PermissionType.ACTION_CREATE))
        self.assertFalse(resolver.user_has_permission(user_db=user_db,
            permission_type=PermissionType.RULE_CREATE))

        # Custom role with permission direct permission on the target action

    def test_user_has_resource_permission(self):
        pass

