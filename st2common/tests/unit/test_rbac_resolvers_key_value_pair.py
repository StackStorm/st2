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
from st2common.persistence.keyvalue import KeyValuePair
from st2common.models.db.keyvalue import KeyValuePairDB
from st2common.rbac.resolvers import KeyValuePermissionsResolver
from tests.unit.test_rbac_resolvers import BasePermissionsResolverTestCase

__all__ = [
    'KeyValuePermissionsResolver'
]


class KeyValuePermissionsResolverTestCase(BasePermissionsResolverTestCase):
    def setUp(self):
        super(KeyValuePermissionsResolverTestCase, self).setUp()

        kvp_1_db = KeyValuePairDB(name='key1', value='val1')
        kvp_1_db = KeyValuePair.add_or_update(kvp_1_db)
        self.resources['kvp_1'] = kvp_1_db

    def test_user_has_resource_db_permission(self):
        # Note: Right now we don't support granting permissions on key value items so we just check
        # that the method always returns True
        resolver = KeyValuePermissionsResolver()

        # No roles
        user_db = self.users['no_roles']
        resource_db = self.resources['kvp_1']

        permission_types = PermissionType.get_valid_permissions_for_resource_type(
            ResourceType.KEY_VALUE_PAIR)

        self.assertUserHasResourceDbPermissions(
            resolver=resolver,
            user_db=user_db,
            resource_db=resource_db,
            permission_types=permission_types)
