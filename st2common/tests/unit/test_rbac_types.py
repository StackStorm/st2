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

from unittest2 import TestCase

from st2common.constants.types import ResourceType as SystemType
from st2common.rbac.types import PermissionType
from st2common.rbac.types import ResourceType


class RBACPermissionTypeTestCase(TestCase):

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
        self.assertEqual(PermissionType.get_resource_type(PermissionType.PACK_LIST),
                         SystemType.PACK)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.PACK_VIEW),
                         SystemType.PACK)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.PACK_CREATE),
                         SystemType.PACK)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.PACK_MODIFY),
                         SystemType.PACK)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.PACK_DELETE),
                         SystemType.PACK)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.PACK_ALL),
                         SystemType.PACK)

        self.assertEqual(PermissionType.get_resource_type(PermissionType.SENSOR_LIST),
                         SystemType.SENSOR_TYPE)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.SENSOR_VIEW),
                         SystemType.SENSOR_TYPE)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.SENSOR_MODIFY),
                         SystemType.SENSOR_TYPE)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.SENSOR_ALL),
                         SystemType.SENSOR_TYPE)

        self.assertEqual(PermissionType.get_resource_type(PermissionType.ACTION_LIST),
                         SystemType.ACTION)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.ACTION_VIEW),
                         SystemType.ACTION)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.ACTION_CREATE),
                         SystemType.ACTION)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.ACTION_MODIFY),
                         SystemType.ACTION)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.ACTION_DELETE),
                         SystemType.ACTION)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.ACTION_EXECUTE),
                         SystemType.ACTION)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.ACTION_ALL),
                         SystemType.ACTION)

        self.assertEqual(PermissionType.get_resource_type(PermissionType.EXECUTION_LIST),
                         SystemType.EXECUTION)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.EXECUTION_VIEW),
                         SystemType.EXECUTION)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.EXECUTION_RE_RUN),
                         SystemType.EXECUTION)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.EXECUTION_STOP),
                         SystemType.EXECUTION)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.EXECUTION_ALL),
                         SystemType.EXECUTION)

        self.assertEqual(PermissionType.get_resource_type(PermissionType.RULE_LIST),
                         SystemType.RULE)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.RULE_VIEW),
                         SystemType.RULE)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.RULE_CREATE),
                         SystemType.RULE)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.RULE_MODIFY),
                         SystemType.RULE)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.RULE_DELETE),
                         SystemType.RULE)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.RULE_ALL),
                         SystemType.RULE)

        self.assertEqual(PermissionType.get_resource_type(PermissionType.KEY_VALUE_VIEW),
                         SystemType.KEY_VALUE_PAIR)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.KEY_VALUE_SET),
                         SystemType.KEY_VALUE_PAIR)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.KEY_VALUE_DELETE),
                         SystemType.KEY_VALUE_PAIR)

        self.assertEqual(PermissionType.get_resource_type(PermissionType.WEBHOOK_CREATE),
                         SystemType.WEBHOOK)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.WEBHOOK_SEND),
                         SystemType.WEBHOOK)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.WEBHOOK_DELETE),
                         SystemType.WEBHOOK)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.WEBHOOK_ALL),
                         SystemType.WEBHOOK)

        self.assertEqual(PermissionType.get_resource_type(PermissionType.API_KEY_LIST),
                         SystemType.API_KEY)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.API_KEY_VIEW),
                         SystemType.API_KEY)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.API_KEY_CREATE),
                         SystemType.API_KEY)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.API_KEY_DELETE),
                         SystemType.API_KEY)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.API_KEY_ALL),
                         SystemType.API_KEY)

    def test_get_permission_type(self):
        self.assertEqual(PermissionType.get_permission_type(resource_type=ResourceType.ACTION,
                                                            permission_name='view'),
                        PermissionType.ACTION_VIEW)
        self.assertEqual(PermissionType.get_permission_type(resource_type=ResourceType.ACTION,
                                                            permission_name='all'),
                        PermissionType.ACTION_ALL)
        self.assertEqual(PermissionType.get_permission_type(resource_type=ResourceType.ACTION,
                                                            permission_name='execute'),
                        PermissionType.ACTION_EXECUTE)
        self.assertEqual(PermissionType.get_permission_type(resource_type=ResourceType.RULE,
                                                            permission_name='view'),
                        PermissionType.RULE_VIEW)
        self.assertEqual(PermissionType.get_permission_type(resource_type=ResourceType.RULE,
                                                            permission_name='delete'),
                        PermissionType.RULE_DELETE)

    def test_get_permission_name(self):
        self.assertEqual(PermissionType.get_permission_name(PermissionType.ACTION_LIST),
                         'list')
        self.assertEqual(PermissionType.get_permission_name(PermissionType.ACTION_CREATE),
                         'create')
        self.assertEqual(PermissionType.get_permission_name(PermissionType.ACTION_DELETE),
                         'delete')
        self.assertEqual(PermissionType.get_permission_name(PermissionType.ACTION_ALL),
                         'all')
        self.assertEqual(PermissionType.get_permission_name(PermissionType.PACK_ALL),
                         'all')
        self.assertEqual(PermissionType.get_permission_name(PermissionType.SENSOR_MODIFY),
                         'modify')
        self.assertEqual(PermissionType.get_permission_name(PermissionType.ACTION_EXECUTE),
                         'execute')
