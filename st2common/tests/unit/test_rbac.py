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

from __future__ import absolute_import

import unittest2
from oslo_config import cfg

from st2tests import config
from st2tests.base import CleanDbTestCase
from st2common.rbac import utils
from st2common.rbac.types import PermissionType
from st2common.rbac.types import ResourceType
from st2common.rbac.backends import get_backend_instance
from st2common.models.db.auth import UserDB
from st2common.models.db.rbac import RoleDB
from st2common.persistence.rbac import Role
from st2common.services.rbac import get_all_roles
from st2common.rbac.migrations import insert_system_roles

__all__ = [
    'RBACUtilsTestCase',
    'RBACMigrationsTestCase',
    'RBACRoleDBTestCase'
]


class RBACUtilsTestCase(CleanDbTestCase):
    @classmethod
    def setUpClass(cls):
        super(RBACUtilsTestCase, cls).setUpClass()
        config.parse_args()

    def setUp(self):
        super(RBACUtilsTestCase, self).setUp()
        self.mocks = {}

        user_db = UserDB(name='test1')
        self.mocks['user_db'] = user_db

    def test_feature_flag_returns_true_on_rbac_disabled(self):
        # When feature RBAC is disabled, all the functions should return True
        cfg.CONF.set_override(name='enable', override=False, group='rbac')

        result = utils.user_is_admin(user_db=self.mocks['user_db'])
        self.assertTrue(result)

    def test_feature_flag_returns_false_on_rbac_enabled(self):
        cfg.CONF.set_override(name='enable', override=True, group='rbac')

        # TODO: Enable once checks are implemented
        return
        result = utils.user_is_admin(user_db=self.mocks['user_db'])
        self.assertFalse(result)


class RBACMigrationsTestCase(CleanDbTestCase):
    @classmethod
    def setUpClass(cls):
        super(RBACMigrationsTestCase, cls).setUpClass()
        config.parse_args()

    def test_insert_system_roles(self):
        role_dbs = get_all_roles()
        self.assertItemsEqual(role_dbs, [])

        insert_system_roles()

        role_dbs = get_all_roles()
        self.assertTrue(len(role_dbs), 3)

        role_names = [role_db.name for role_db in role_dbs]
        self.assertTrue('system_admin' in role_names)
        self.assertTrue('admin' in role_names)
        self.assertTrue('observer' in role_names)


class RBACRoleDBTestCase(CleanDbTestCase):

    @classmethod
    def setUpClass(cls):
        super(RBACRoleDBTestCase, cls).setUpClass()
        config.parse_args()

    def test_insert(self):
        role_db = RoleDB(name='role-1', description='test role', system=True)
        created = Role.insert(role_db)
        retrieved = Role.get_by_id(created.id)
        self.assertEqual(retrieved.name, role_db.name, 'Failed to save RoleDB object.')


class NoOpRBACBackendTestCase(unittest2.TestCase):
    def test_noop_backend(self):
        backend = get_backend_instance(name='noop')

        resolver = backend.get_resolver_for_permission_type(
            permission_type=PermissionType.ACTION_VIEW)
        self.assertTrue(resolver.user_has_permission(None, None))
        self.assertTrue(resolver.user_has_resource_api_permission(None, None, None))
        self.assertTrue(resolver.user_has_resource_db_permission(None, None, None))

        resolver = backend.get_resolver_for_resource_type(resource_type=ResourceType.ACTION)
        self.assertTrue(resolver.user_has_permission(None, None))
        self.assertTrue(resolver.user_has_resource_api_permission(None, None, None))
        self.assertTrue(resolver.user_has_resource_db_permission(None, None, None))

        remote_group_syncer = backend.get_remote_group_to_role_syncer()
        self.assertEqual(remote_group_syncer.sync(None, None), [])
