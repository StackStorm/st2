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

import unittest2
from oslo_config import cfg

from st2tests import config
from st2tests.base import CleanDbTestCase
from st2common.rbac import utils
from st2common.rbac.types import PermissionType
from st2common.rbac.types import ResourceType
from st2common.models.db.auth import UserDB


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


class RBACPermissionTypeTestCase(unittest2.TestCase):
    def test_get_valid_permission_for_resource_type(self):
        valid_action_permissions = PermissionType.get_valid_permissions_for_resource_type(
            resource_type=ResourceType.ACTION)

        for name in valid_action_permissions:
            self.assertTrue(name.startswith(ResourceType.ACTION + '_'))

        valid_rule_permissions = PermissionType.get_valid_permissions_for_resource_type(
            resource_type=ResourceType.RULE)

        for name in valid_rule_permissions:
            self.assertTrue(name.startswith(ResourceType.RULE + '_'))

    def test_get_resource_type(self):
        self.assertEqual(PermissionType.get_resource_type(PermissionType.ACTION_CREATE),
                         ResourceType.ACTION)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.ACTION_DELETE),
                         ResourceType.ACTION)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.ACTION_ALL),
                         ResourceType.ACTION)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.PACK_ALL),
                         ResourceType.PACK)

    def test_get_permission_name(self):
        self.assertEqual(PermissionType.get_permission_name(PermissionType.ACTION_CREATE),
                         'create')
        self.assertEqual(PermissionType.get_permission_name(PermissionType.ACTION_DELETE),
                         'delete')
        self.assertEqual(PermissionType.get_permission_name(PermissionType.ACTION_ALL),
                         'all')
        self.assertEqual(PermissionType.get_permission_name(PermissionType.PACK_ALL),
                         'all')
