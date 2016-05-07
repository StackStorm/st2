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
from st2common.persistence.sensor import SensorType
from st2common.models.db.auth import UserDB
from st2common.models.db.rbac import RoleDB
from st2common.models.db.rbac import UserRoleAssignmentDB
from st2common.models.db.rbac import PermissionGrantDB
from st2common.models.db.sensor import SensorTypeDB
from st2common.rbac.resolvers import SensorPermissionsResolver
from tests.unit.test_rbac_resolvers import BasePermissionsResolverTestCase


__all__ = [
    'SensorPermissionsResolverTestCase'
]


class SensorPermissionsResolverTestCase(BasePermissionsResolverTestCase):
    def setUp(self):
        super(SensorPermissionsResolverTestCase, self).setUp()

        # Create some mock users
        user_1_db = UserDB(name='1_role_sensor_pack_grant')
        user_1_db = User.add_or_update(user_1_db)
        self.users['custom_role_sensor_pack_grant'] = user_1_db

        user_2_db = UserDB(name='1_role_sensor_grant')
        user_2_db = User.add_or_update(user_2_db)
        self.users['custom_role_sensor_grant'] = user_2_db

        user_3_db = UserDB(name='custom_role_pack_sensor_all_grant')
        user_3_db = User.add_or_update(user_3_db)
        self.users['custom_role_pack_sensor_all_grant'] = user_3_db

        user_4_db = UserDB(name='custom_role_sensor_all_grant')
        user_4_db = User.add_or_update(user_4_db)
        self.users['custom_role_sensor_all_grant'] = user_4_db

        user_5_db = UserDB(name='custom_role_sensor_list_grant')
        user_5_db = User.add_or_update(user_5_db)
        self.users['custom_role_sensor_list_grant'] = user_5_db

        # Create some mock resources on which permissions can be granted
        sensor_1_db = SensorTypeDB(pack='test_pack_1', name='sensor1')
        sensor_1_db = SensorType.add_or_update(sensor_1_db)
        self.resources['sensor_1'] = sensor_1_db

        sensor_2_db = SensorTypeDB(pack='test_pack_1', name='sensor2')
        sensor_2_db = SensorType.add_or_update(sensor_2_db)
        self.resources['sensor_2'] = sensor_2_db

        sensor_3_db = SensorTypeDB(pack='test_pack_2', name='sensor3')
        sensor_3_db = SensorType.add_or_update(sensor_3_db)
        self.resources['sensor_3'] = sensor_3_db

        # Create some mock roles with associated permission grants
        # Custom role 2 - one grant on parent pack
        # "sensor_view" on pack_1
        grant_db = PermissionGrantDB(resource_uid=self.resources['pack_1'].get_uid(),
                                     resource_type=ResourceType.PACK,
                                     permission_types=[PermissionType.SENSOR_VIEW])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_3_db = RoleDB(name='custom_role_sensor_pack_grant',
                           permission_grants=permission_grants)
        role_3_db = Role.add_or_update(role_3_db)
        self.roles['custom_role_sensor_pack_grant'] = role_3_db

        # Custom role 4 - one grant on pack
        # "sensor_view on sensor_3
        grant_db = PermissionGrantDB(resource_uid=self.resources['sensor_3'].get_uid(),
                                     resource_type=ResourceType.SENSOR,
                                     permission_types=[PermissionType.SENSOR_VIEW])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_4_db = RoleDB(name='custom_role_sensor_grant', permission_grants=permission_grants)
        role_4_db = Role.add_or_update(role_4_db)
        self.roles['custom_role_sensor_grant'] = role_4_db

        # Custom role - "sensor_all" grant on a parent sensor pack
        grant_db = PermissionGrantDB(resource_uid=self.resources['pack_1'].get_uid(),
                                     resource_type=ResourceType.PACK,
                                     permission_types=[PermissionType.SENSOR_ALL])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_4_db = RoleDB(name='custom_role_pack_sensor_all_grant',
                           permission_grants=permission_grants)
        role_4_db = Role.add_or_update(role_4_db)
        self.roles['custom_role_pack_sensor_all_grant'] = role_4_db

        # Custom role - "sensor_all" grant on a sensor
        grant_db = PermissionGrantDB(resource_uid=self.resources['sensor_1'].get_uid(),
                                     resource_type=ResourceType.SENSOR,
                                     permission_types=[PermissionType.SENSOR_ALL])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_4_db = RoleDB(name='custom_role_sensor_all_grant', permission_grants=permission_grants)
        role_4_db = Role.add_or_update(role_4_db)
        self.roles['custom_role_sensor_all_grant'] = role_4_db

        # Custom role - "sensor_list" grant
        grant_db = PermissionGrantDB(resource_uid=None,
                                     resource_type=None,
                                     permission_types=[PermissionType.SENSOR_LIST])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_5_db = RoleDB(name='custom_role_sensor_list_grant',
                           permission_grants=permission_grants)
        role_5_db = Role.add_or_update(role_5_db)
        self.roles['custom_role_sensor_list_grant'] = role_5_db

        # Create some mock role assignments
        user_db = self.users['custom_role_sensor_pack_grant']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['custom_role_sensor_pack_grant'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        user_db = self.users['custom_role_sensor_grant']
        role_assignment_db = UserRoleAssignmentDB(user=user_db.name,
                                                  role=self.roles['custom_role_sensor_grant'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        user_db = self.users['custom_role_pack_sensor_all_grant']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['custom_role_pack_sensor_all_grant'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        user_db = self.users['custom_role_sensor_all_grant']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['custom_role_sensor_all_grant'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        user_db = self.users['custom_role_sensor_list_grant']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['custom_role_sensor_list_grant'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

    def test_user_has_permission(self):
        resolver = SensorPermissionsResolver()

        # Admin user, should always return true
        user_db = self.users['admin']
        self.assertUserHasPermission(resolver=resolver,
                                     user_db=user_db,
                                     permission_type=PermissionType.SENSOR_LIST)

        # Observer, should always return true for VIEW permissions
        user_db = self.users['observer']
        self.assertUserHasPermission(resolver=resolver,
                                     user_db=user_db,
                                     permission_type=PermissionType.SENSOR_LIST)

        # No roles, should return false for everything
        user_db = self.users['no_roles']
        self.assertUserDoesntHavePermission(resolver=resolver,
                                            user_db=user_db,
                                            permission_type=PermissionType.SENSOR_LIST)

        # Custom role with no permission grants, should return false for everything
        user_db = self.users['1_custom_role_no_permissions']
        self.assertUserDoesntHavePermission(resolver=resolver,
                                            user_db=user_db,
                                            permission_type=PermissionType.SENSOR_LIST)

        # Custom role with "sensor_list" grant
        user_db = self.users['custom_role_sensor_list_grant']
        self.assertUserHasPermission(resolver=resolver,
                                     user_db=user_db,
                                     permission_type=PermissionType.SENSOR_LIST)

    def test_user_has_resource_db_permission(self):
        resolver = SensorPermissionsResolver()
        all_permission_types = PermissionType.get_valid_permissions_for_resource_type(
            ResourceType.SENSOR)

        # Admin user, should always return true
        resource_db = self.resources['sensor_1']
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
            resource_db=self.resources['sensor_1'],
            permission_type=PermissionType.SENSOR_VIEW)
        self.assertUserHasResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=self.resources['sensor_2'],
            permission_type=PermissionType.SENSOR_VIEW)

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
        user_db = self.users['custom_role_pack_grant']
        self.assertUserDoesntHaveResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=self.resources['sensor_1'],
            permission_type=PermissionType.SENSOR_VIEW)
        self.assertUserDoesntHaveResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=self.resources['sensor_2'],
            permission_type=PermissionType.SENSOR_ALL)
        self.assertUserDoesntHaveResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=self.resources['sensor_3'],
            permission_type=PermissionType.SENSOR_VIEW)

        # Custom role with with grant on the parent pack
        user_db = self.users['custom_role_sensor_pack_grant']
        self.assertUserHasResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=self.resources['sensor_1'],
            permission_type=PermissionType.SENSOR_VIEW)
        self.assertUserHasResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=self.resources['sensor_2'],
            permission_type=PermissionType.SENSOR_VIEW)

        self.assertUserDoesntHaveResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=self.resources['sensor_3'],
            permission_type=PermissionType.SENSOR_VIEW)

        # Custom role with a direct grant on sensor
        user_db = self.users['custom_role_sensor_grant']
        self.assertUserHasResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=self.resources['sensor_3'],
            permission_type=PermissionType.SENSOR_VIEW)

        self.assertUserDoesntHaveResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=self.resources['sensor_3'],
            permission_type=PermissionType.SENSOR_ALL)

        # Custom role - "sensor_all" grant on the sensor parent pack
        user_db = self.users['custom_role_pack_sensor_all_grant']
        resource_db = self.resources['sensor_1']
        self.assertUserHasResourceDbPermissions(
            resolver=resolver,
            user_db=user_db,
            resource_db=resource_db,
            permission_types=all_permission_types)

        # Custom role - "sensor_all" grant on the sensor
        user_db = self.users['custom_role_sensor_all_grant']
        resource_db = self.resources['sensor_1']
        self.assertUserHasResourceDbPermissions(
            resolver=resolver,
            user_db=user_db,
            resource_db=resource_db,
            permission_types=all_permission_types)
