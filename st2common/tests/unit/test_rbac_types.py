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

from st2common.constants.types import ResourceType as systemtypes
from st2common.rbac.types import PermissionType


class RBACTypeTestCase(TestCase):

    def test_get_resource_type(self):
        self.assertEqual(PermissionType.get_resource_type(PermissionType.PACK_VIEW),
                         systemtypes.PACK)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.PACK_CREATE),
                         systemtypes.PACK)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.PACK_MODIFY),
                         systemtypes.PACK)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.PACK_DELETE),
                         systemtypes.PACK)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.PACK_ALL),
                         systemtypes.PACK)

        self.assertEqual(PermissionType.get_resource_type(PermissionType.SENSOR_VIEW),
                         systemtypes.SENSOR_TYPE)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.SENSOR_ALL),
                         systemtypes.SENSOR_TYPE)

        self.assertEqual(PermissionType.get_resource_type(PermissionType.ACTION_VIEW),
                         systemtypes.ACTION)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.ACTION_CREATE),
                         systemtypes.ACTION)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.ACTION_MODIFY),
                         systemtypes.ACTION)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.ACTION_DELETE),
                         systemtypes.ACTION)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.ACTION_EXECUTE),
                         systemtypes.ACTION)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.ACTION_ALL),
                         systemtypes.ACTION)

        self.assertEqual(PermissionType.get_resource_type(PermissionType.EXECUTION_VIEW),
                         systemtypes.EXECUTION)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.EXECUTION_RE_RUN),
                         systemtypes.EXECUTION)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.EXECUTION_STOP),
                         systemtypes.EXECUTION)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.EXECUTION_ALL),
                         systemtypes.EXECUTION)

        self.assertEqual(PermissionType.get_resource_type(PermissionType.RULE_VIEW),
                         systemtypes.RULE)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.RULE_CREATE),
                         systemtypes.RULE)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.RULE_MODIFY),
                         systemtypes.RULE)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.RULE_DELETE),
                         systemtypes.RULE)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.RULE_ALL),
                         systemtypes.RULE)

        self.assertEqual(PermissionType.get_resource_type(PermissionType.KEY_VALUE_VIEW),
                         systemtypes.KEY_VALUE_PAIR)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.KEY_VALUE_SET),
                         systemtypes.KEY_VALUE_PAIR)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.KEY_VALUE_DELETE),
                         systemtypes.KEY_VALUE_PAIR)

        self.assertEqual(PermissionType.get_resource_type(PermissionType.WEBHOOK_CREATE),
                         systemtypes.WEBHOOK)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.WEBHOOK_SEND),
                         systemtypes.WEBHOOK)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.WEBHOOK_DELETE),
                         systemtypes.WEBHOOK)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.WEBHOOK_ALL),
                         systemtypes.WEBHOOK)

        self.assertEqual(PermissionType.get_resource_type(PermissionType.API_KEY_VIEW),
                         systemtypes.API_KEY)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.API_KEY_CREATE),
                         systemtypes.API_KEY)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.API_KEY_DELETE),
                         systemtypes.API_KEY)
        self.assertEqual(PermissionType.get_resource_type(PermissionType.API_KEY_ALL),
                         systemtypes.API_KEY)
