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
import mock

from st2common.services import triggers as trigger_service
with mock.patch.object(trigger_service, 'create_trigger_type_db', mock.MagicMock()):
    from st2api.controllers.v1.webhooks import HooksHolder

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
from st2common.models.db.webhook import WebhookDB
from st2tests.fixturesloader import FixturesLoader
from tests.base import APIControllerWithRBACTestCase

from tests.unit.controllers.v1.test_webhooks import DUMMY_TRIGGER_DB
from tests.unit.controllers.v1.test_webhooks import DUMMY_TRIGGER_API

http_client = six.moves.http_client

__all__ = [
    'WebhookControllerRBACTestCase'
]


class WebhookControllerRBACTestCase(APIControllerWithRBACTestCase):
    fixtures_loader = FixturesLoader()

    def setUp(self):
        super(WebhookControllerRBACTestCase, self).setUp()

        # Insert mock users, roles and assignments

        # Users
        user_1_db = UserDB(name='webhook_list')
        user_1_db = User.add_or_update(user_1_db)
        self.users['webhook_list'] = user_1_db

        user_2_db = UserDB(name='webhook_view')
        user_2_db = User.add_or_update(user_2_db)
        self.users['webhook_view'] = user_2_db

        # Roles
        # webhook_list
        grant_db = PermissionGrantDB(resource_uid=None,
                                     resource_type=ResourceType.WEBHOOK,
                                     permission_types=[PermissionType.WEBHOOK_LIST])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_1_db = RoleDB(name='webhook_list', permission_grants=permission_grants)
        role_1_db = Role.add_or_update(role_1_db)
        self.roles['webhook_list'] = role_1_db

        # webhook_view on webhook 1 (git)
        name = 'git'
        webhook_db = WebhookDB(name=name)
        webhook_uid = webhook_db.get_uid()
        grant_db = PermissionGrantDB(resource_uid=webhook_uid,
                                     resource_type=ResourceType.WEBHOOK,
                                     permission_types=[PermissionType.WEBHOOK_VIEW])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_1_db = RoleDB(name='webhook_view', permission_grants=permission_grants)
        role_1_db = Role.add_or_update(role_1_db)
        self.roles['webhook_view'] = role_1_db

        # Role assignments
        role_assignment_db = UserRoleAssignmentDB(
            user=self.users['webhook_list'].name,
            role=self.roles['webhook_list'].name,
            source='assignments/%s.yaml' % self.users['webhook_list'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        role_assignment_db = UserRoleAssignmentDB(
            user=self.users['webhook_view'].name,
            role=self.roles['webhook_view'].name,
            source='assignments/%s.yaml' % self.users['webhook_view'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

    def test_get_all_no_permissions(self):
        user_db = self.users['no_permissions']
        self.use_user(user_db)

        resp = self.app.get('/v1/webhooks', expect_errors=True)
        expected_msg = ('User "no_permissions" doesn\'t have required permission "webhook_list"')
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    @mock.patch.object(HooksHolder, 'get_triggers_for_hook', mock.MagicMock(
        return_value=[DUMMY_TRIGGER_API]))
    def test_get_one_no_permissions(self):
        user_db = self.users['no_permissions']
        self.use_user(user_db)

        name = 'git'
        webhook_db = WebhookDB(name=name)
        webhook_id = name
        webhook_uid = webhook_db.get_uid()

        resp = self.app.get('/v1/webhooks/%s' % (webhook_id), expect_errors=True)
        expected_msg = ('User "no_permissions" doesn\'t have required permission "webhook_view"'
                        ' on resource "%s"' % (webhook_uid))
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    @mock.patch.object(HooksHolder, 'get_all', mock.MagicMock(
        return_value=[DUMMY_TRIGGER_API]))
    @mock.patch.object(HooksHolder, 'get_triggers_for_hook', mock.MagicMock(
        return_value=[DUMMY_TRIGGER_API]))
    def test_get_all_permission_success_get_one_no_permission_failure(self):
        user_db = self.users['webhook_list']
        self.use_user(user_db)

        # webhook_list permission, but no webhook_view permission
        resp = self.app.get('/v1/webhooks')
        self.assertEqual(resp.status_code, http_client.OK)
        self.assertEqual(len(resp.json), 1)

        name = 'git'
        webhook_db = WebhookDB(name=name)
        webhook_id = name
        webhook_uid = webhook_db.get_uid()

        resp = self.app.get('/v1/webhooks/%s' % (webhook_id), expect_errors=True)
        expected_msg = ('User "webhook_list" doesn\'t have required permission "webhook_view"'
                        ' on resource "%s"' % (webhook_uid))
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    @mock.patch.object(HooksHolder, 'get_all', mock.MagicMock(
        return_value=[DUMMY_TRIGGER_API]))
    @mock.patch.object(HooksHolder, 'get_triggers_for_hook', mock.MagicMock(
        return_value=[DUMMY_TRIGGER_API]))
    def test_get_one_permission_success_get_all_no_permission_failure(self):
        user_db = self.users['webhook_view']
        self.use_user(user_db)

        # webhook_view permission, but no webhook_list permission
        name = 'git'
        webhook_id = name

        resp = self.app.get('/v1/webhooks/%s' % (webhook_id))
        self.assertEqual(resp.status_code, http_client.OK)
        self.assertEqual(resp.json['ref'], DUMMY_TRIGGER_DB.ref)

        resp = self.app.get('/v1/webhooks', expect_errors=True)
        expected_msg = ('User "webhook_view" doesn\'t have required permission "webhook_list"')
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)
