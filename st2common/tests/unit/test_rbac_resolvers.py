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
import unittest2
from oslo_config import cfg

from st2common.services import rbac as rbac_services
from st2common.rbac.types import PermissionType
from st2common.rbac.types import ResourceType
from st2common.rbac.types import SystemRole
from st2common.persistence.auth import User
from st2common.persistence.rbac import Role
from st2common.persistence.rbac import UserRoleAssignment
from st2common.persistence.rbac import PermissionGrant
from st2common.persistence.pack import Pack
from st2common.models.db.auth import UserDB
from st2common.models.db.rbac import RoleDB
from st2common.models.db.rbac import UserRoleAssignmentDB
from st2common.models.db.rbac import PermissionGrantDB
from st2common.models.db.pack import PackDB
from st2common.rbac.resolvers import get_resolver_for_resource_type
from st2common.rbac.migrations import insert_system_roles
from st2tests.base import CleanDbTestCase

__all__ = [
    'BasePermissionsResolverTestCase',
    'PermissionsResolverUtilsTestCase'
]


class BasePermissionsResolverTestCase(CleanDbTestCase):
    def setUp(self):
        super(BasePermissionsResolverTestCase, self).setUp()

        # Make sure RBAC is enabeld
        cfg.CONF.set_override(name='enable', override=True, group='rbac')

        self.users = {}
        self.roles = {}
        self.resources = {}

        # Run role "migrations"
        insert_system_roles()

        # Insert common mock objects
        self._insert_common_mocks()

    def assertUserHasPermission(self, resolver, user_db, permission_type):
        """
        Assert that the user has the provided permission.
        """
        self.assertTrue(isinstance(permission_type, six.string_types))

        result = resolver.user_has_permission(user_db=user_db,
                                              permission_type=permission_type)

        if not result:
            msg = ('Expected permission grant "%s" for user "%s" but no grant was found' %
                   (permission_type, user_db.name))
            raise AssertionError(msg)

        return True

    def assertUserDoesntHavePermission(self, resolver, user_db, permission_type):
        """
        Assert that the user has the provided permission.
        """
        self.assertTrue(isinstance(permission_type, six.string_types))

        result = resolver.user_has_permission(user_db=user_db,
                                              permission_type=permission_type)

        if result:
            msg = ('Found permission grant "%s" for user "%s" which shouldn\'t exist' %
                   (permission_type, user_db.name))
            raise AssertionError(msg)

        return True

    def assertUserHasResourceDbPermission(self, resolver, user_db, resource_db, permission_type):
        """
        Assert that the user has the provided permission on the provided resource.
        """
        self.assertTrue(isinstance(permission_type, six.string_types))

        result = resolver.user_has_resource_db_permission(user_db=user_db, resource_db=resource_db,
                                                          permission_type=permission_type)

        if not result:
            msg = ('Expected permission grant "%s" for user "%s" on resource DB "%s", but no '
                   'grant was found' % (permission_type, user_db.name, resource_db.get_uid()))
            raise AssertionError(msg)

        return True

    def assertUserDoesntHaveResourceDbPermission(self, resolver, user_db, resource_db,
                                                 permission_type):
        """
        Assert that the user has the provided permission on the provided resource.
        """
        self.assertTrue(isinstance(permission_type, six.string_types))

        result = resolver.user_has_resource_db_permission(user_db=user_db, resource_db=resource_db,
                                                          permission_type=permission_type)

        if result:
            msg = ('Found permission grant "%s" for user "%s" on resource DB "%s", which '
                   'shouldn\'t exist' % (permission_type, user_db.name, resource_db.get_uid()))
            raise AssertionError(msg)

        return True

    def assertUserHasResourceDbPermissions(self, resolver, user_db, resource_db, permission_types):
        """
        Assert that the user has all the specified permissions on the provided resource.

        If permission grant is not found, an AssertionError is thrown.
        """
        self.assertTrue(isinstance(permission_types, (list, tuple)))
        self.assertTrue(len(permission_types) > 1)

        for permission_type in permission_types:
            self.assertUserHasResourceDbPermission(resolver=resolver, user_db=user_db,
                                                   resource_db=resource_db,
                                                   permission_type=permission_type)

        return True

    def assertUserDoesntHaveResourceDbPermissions(self, resolver, user_db, resource_db,
                                                  permission_types):
        """
        Assert that the user doesn't have all the specified permissions on the provided resource.

        If a permission grant which shouldn't exist is found, an AssertionError is thrown.
        """
        self.assertTrue(isinstance(permission_types, (list, tuple)))
        self.assertTrue(len(permission_types) > 1)

        for permission_type in permission_types:
            self.assertUserDoesntHaveResourceDbPermission(resolver=resolver, user_db=user_db,
                                                          resource_db=resource_db,
                                                          permission_type=permission_type)

        return True

    def assertUserHasResourceApiPermission(self, resolver, user_db, resource_api, permission_type):
        self.assertTrue(isinstance(permission_type, six.string_types))

        result = resolver.user_has_resource_api_permission(user_db=user_db,
                                                           resource_api=resource_api,
                                                           permission_type=permission_type)

        if not result:
            msg = ('Expected permission grant "%s" for user "%s" on resource API "%s", but no '
                   'grant was found' % (permission_type, user_db.name, resource_api.get_uid()))
            raise AssertionError(msg)

        return True

    def assertUserDoesntHaveResourceApiPermission(self, resolver, user_db, resource_api,
                                                  permission_type):
        self.assertTrue(isinstance(permission_type, six.string_types))

        result = resolver.user_has_resource_api_permission(user_db=user_db,
                                                           resource_api=resource_api,
                                                           permission_type=permission_type)

        if result:
            msg = ('Found permission grant "%s" for user "%s" on resource API "%s", which '
                   'shouldn\'t exist' % (permission_type, user_db.name, resource_api.get_uid()))
            raise AssertionError(msg)

        return True

    def _insert_common_mocks(self):
        self._insert_common_mock_users()
        self._insert_common_mock_resources()
        self._insert_common_mock_roles()
        self._insert_common_mock_role_assignments()

    def _insert_common_mock_users(self):
        # Insert common mock users
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

    def _insert_common_mock_resources(self):
        pack_1_db = PackDB(name='test_pack_1', ref='test_pack_1', description='',
                           version='0.1.0', author='foo', email='test@example.com')
        pack_1_db = Pack.add_or_update(pack_1_db)
        self.resources['pack_1'] = pack_1_db

        pack_2_db = PackDB(name='test_pack_2', ref='test_pack_2', description='',
                           version='0.1.0', author='foo', email='test@example.com')
        pack_2_db = Pack.add_or_update(pack_2_db)
        self.resources['pack_2'] = pack_2_db

    def _insert_common_mock_roles(self):
        # Insert common mock roles
        admin_role_db = rbac_services.get_role_by_name(name=SystemRole.ADMIN)
        observer_role_db = rbac_services.get_role_by_name(name=SystemRole.OBSERVER)
        self.roles['admin_role'] = admin_role_db
        self.roles['observer_role'] = observer_role_db

        # Custom role 1 - no grants
        role_1_db = rbac_services.create_role(name='custom_role_1')
        self.roles['custom_role_1'] = role_1_db

        # Custom role 2 - one grant on pack_1
        # "pack_create" on pack_1
        grant_db = PermissionGrantDB(resource_uid=self.resources['pack_1'].get_uid(),
                                     resource_type=ResourceType.PACK,
                                     permission_types=[PermissionType.PACK_CREATE])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_3_db = RoleDB(name='custom_role_pack_grant', permission_grants=permission_grants)
        role_3_db = Role.add_or_update(role_3_db)
        self.roles['custom_role_pack_grant'] = role_3_db

    def _insert_common_mock_role_assignments(self):
        # Insert common mock role assignments
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


class PermissionsResolverUtilsTestCase(unittest2.TestCase):
    def test_get_resolver_for_resource_type_valid_resource_type(self):
        valid_resources_types = [ResourceType.PACK, ResourceType.SENSOR, ResourceType.ACTION,
                                 ResourceType.RULE, ResourceType.RULE_ENFORCEMENT,
                                 ResourceType.EXECUTION,
                                 ResourceType.KEY_VALUE_PAIR,
                                 ResourceType.WEBHOOK]

        for resource_type in valid_resources_types:
            resolver_instance = get_resolver_for_resource_type(resource_type=resource_type)
            resource_name = resource_type.split('_')[0].lower()
            class_name = resolver_instance.__class__.__name__.lower()
            self.assertTrue(resource_name in class_name)

    def test_get_resolver_for_resource_type_unsupported_resource_type(self):
        expected_msg = 'Unsupported resource: alias'
        self.assertRaisesRegexp(ValueError, expected_msg, get_resolver_for_resource_type,
                                resource_type='alias')
