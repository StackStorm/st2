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

import copy
import httplib

import mock
import six

from st2common.transport.publishers import PoolPublisher
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
from st2tests.fixturesloader import FixturesLoader
from tests.base import APIControllerWithRBACTestCase

http_client = six.moves.http_client

__all__ = [
    'RuleControllerRBACTestCase'
]

FIXTURES_PACK = 'generic'
TEST_FIXTURES = {
    'runners': ['testrunner1.yaml'],
    'actions': ['action1.yaml', 'local.yaml'],
    'triggers': ['trigger1.yaml'],
    'triggertypes': ['triggertype1.yaml']
}


class RuleControllerRBACTestCase(APIControllerWithRBACTestCase):
    fixtures_loader = FixturesLoader()

    def setUp(self):
        super(RuleControllerRBACTestCase, self).setUp()
        self.fixtures_loader.save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                                 fixtures_dict=TEST_FIXTURES)

        file_name = 'rule_with_webhook_trigger.yaml'
        self.RULE_1 = self.fixtures_loader.load_fixtures(
            fixtures_pack=FIXTURES_PACK,
            fixtures_dict={'rules': [file_name]})['rules'][file_name]

        file_name = 'rule_example_pack.yaml'
        self.RULE_2 = self.fixtures_loader.load_fixtures(
            fixtures_pack=FIXTURES_PACK,
            fixtures_dict={'rules': [file_name]})['rules'][file_name]

        # Insert mock users, roles and assignments

        # Users
        permissions = [PermissionType.RULE_CREATE,
                       PermissionType.RULE_VIEW,
                       PermissionType.RULE_MODIFY,
                       PermissionType.RULE_DELETE]

        for name in permissions:
            user_db = UserDB(name=name)
            user_db = User.add_or_update(user_db)
            self.users[name] = user_db

            # Roles
            # action_create grant on parent pack
            grant_db = PermissionGrantDB(resource_uid='pack:examples',
                                         resource_type=ResourceType.PACK,
                                         permission_types=[name])
            grant_db = PermissionGrant.add_or_update(grant_db)
            grant_2_db = PermissionGrantDB(resource_uid='action:wolfpack:action-1',
                                           resource_type=ResourceType.ACTION,
                                           permission_types=[PermissionType.ACTION_EXECUTE])
            grant_2_db = PermissionGrant.add_or_update(grant_2_db)
            permission_grants = [str(grant_db.id), str(grant_2_db.id)]
            role_db = RoleDB(name=name, permission_grants=permission_grants)
            role_db = Role.add_or_update(role_db)
            self.roles[name] = role_db

            # Role assignments
            role_assignment_db = UserRoleAssignmentDB(
                user=user_db.name,
                role=role_db.name)
            UserRoleAssignment.add_or_update(role_assignment_db)

        user_1_db = UserDB(name='rule_create_no_execute')
        user_1_db = User.add_or_update(user_1_db)
        self.users['rule_create_no_execute'] = user_1_db

        user_2_db = UserDB(name='rule_create_webhook_create')
        user_2_db = User.add_or_update(user_2_db)
        self.users['rule_create_webhook_create'] = user_2_db

        user_3_db = UserDB(name='rule_create_webhook_create_core_local_execute')
        user_3_db = User.add_or_update(user_3_db)
        self.users['rule_create_webhook_create_core_local_execute'] = user_3_db

        # Roles
        # rule_create grant on parent pack
        grant_db = PermissionGrantDB(resource_uid='pack:examples',
                                     resource_type=ResourceType.PACK,
                                     permission_types=[PermissionType.RULE_CREATE])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_1_db = RoleDB(name='rule_create_no_execute', permission_grants=permission_grants)
        role_1_db = Role.add_or_update(role_1_db)
        self.roles['rule_create_no_execute'] = role_1_db

        # rule_create grant on parent pack, webhook_create on webhook "sample"
        grant_1_db = PermissionGrantDB(resource_uid='pack:examples',
                                     resource_type=ResourceType.PACK,
                                     permission_types=[PermissionType.RULE_CREATE])
        grant_1_db = PermissionGrant.add_or_update(grant_1_db)
        grant_2_db = PermissionGrantDB(resource_uid='webhook:sample',
                                     resource_type=ResourceType.WEBHOOK,
                                     permission_types=[PermissionType.WEBHOOK_CREATE])
        grant_2_db = PermissionGrant.add_or_update(grant_2_db)
        permission_grants = [str(grant_1_db.id), str(grant_2_db.id)]
        role_2_db = RoleDB(name='rule_create_webhook_create', permission_grants=permission_grants)
        role_2_db = Role.add_or_update(role_2_db)
        self.roles['rule_create_webhook_create'] = role_2_db

        # rule_create grant on parent pack, webhook_create on webhook "sample", action_execute on
        # core.local
        grant_1_db = PermissionGrantDB(resource_uid='pack:examples',
                                     resource_type=ResourceType.PACK,
                                     permission_types=[PermissionType.RULE_CREATE])
        grant_1_db = PermissionGrant.add_or_update(grant_1_db)
        grant_2_db = PermissionGrantDB(resource_uid='webhook:sample',
                                     resource_type=ResourceType.WEBHOOK,
                                     permission_types=[PermissionType.WEBHOOK_CREATE])
        grant_2_db = PermissionGrant.add_or_update(grant_2_db)
        grant_3_db = PermissionGrantDB(resource_uid='action:core:local',
                                     resource_type=ResourceType.ACTION,
                                     permission_types=[PermissionType.ACTION_EXECUTE])
        grant_3_db = PermissionGrant.add_or_update(grant_3_db)
        permission_grants = [str(grant_1_db.id), str(grant_2_db.id), str(grant_3_db.id)]
        role_3_db = RoleDB(name='rule_create_webhook_create_core_local_execute',
                           permission_grants=permission_grants)
        role_3_db = Role.add_or_update(role_3_db)
        self.roles['rule_create_webhook_create_core_local_execute'] = role_3_db

        # Role assignments
        user_db = self.users['rule_create_no_execute']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['rule_create_no_execute'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        user_db = self.users['rule_create_webhook_create']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['rule_create_webhook_create'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        user_db = self.users['rule_create_webhook_create_core_local_execute']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['rule_create_webhook_create_core_local_execute'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

    def test_post_webhook_trigger_no_trigger_and_action_permission(self):
        # Test a scenario when user selects a webhook trigger, but only has "rule_create"
        # permission
        user_db = self.users['rule_create_no_execute']
        self.use_user(user_db)

        resp = self.__do_post(self.RULE_1, expect_errors=True)
        expected_msg = ('User "rule_create_no_execute" doesn\'t have required permission (webhook_create) '
                        'to use trigger core.st2.webhook')
        self.assertEqual(resp.status_code, httplib.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_post_no_webhook_trigger(self):
        # Test a scenario when user with only "rule_create" permission selects a non-webhook
        # trigger for which we don't perform any permission checking right now
        user_db = self.users['rule_create_no_execute']
        self.use_user(user_db)

        resp = self.__do_post(self.RULE_2, expect_errors=True)
        expected_msg = ('User "rule_create_no_execute" doesn\'t have required (action_execute) permission '
                        'to use action wolfpack.action-1')
        self.assertEqual(resp.status_code, httplib.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_post_webhook_trigger_webhook_create_permission_no_action_permission(self):
        # Test a scenario where user with "rule_create" and "webhook_create" selects a webhook
        # trigger and core.local action
        user_db = self.users['rule_create_webhook_create']
        self.use_user(user_db)

        resp = self.__do_post(self.RULE_1, expect_errors=True)
        expected_msg = ('User "rule_create_webhook_create" doesn\'t have required '
                        '(action_execute) permission to use action core.local')
        self.assertEqual(resp.status_code, httplib.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_post_action_webhook_trigger_webhook_create_and_action_execute_permission(self):
        # Test a scenario where user selects a webhook trigger and has all the required permissions
        user_db = self.users['rule_create_webhook_create_core_local_execute']
        self.use_user(user_db)

        resp = self.__do_post(self.RULE_1)
        self.assertEqual(resp.status_code, httplib.CREATED)

    def test_get_put_delete_no_permission(self):
        user_db = self.users[PermissionType.RULE_CREATE]
        self.use_user(user_db)

        post_resp = self.__do_post(self.RULE_2)

        user_db = self.users['no_permissions']
        self.use_user(user_db)

        resp = self.__do_get_one(post_resp.json['id'], expect_errors=True)
        expected_msg = ('User "%s" doesn\'t have required permission "%s" on resource "%s"' %
                        ('no_permissions', PermissionType.RULE_VIEW,
                         'rule:examples:rule1'))
        self.assertEqual(resp.status_code, httplib.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

        resp = self.__do_put(post_resp.json['id'], self.RULE_2, expect_errors=True)
        expected_msg = ('User "%s" doesn\'t have required permission "%s" on resource "%s"' %
                        ('no_permissions', PermissionType.RULE_MODIFY,
                         'rule:examples:rule1'))
        self.assertEqual(resp.status_code, httplib.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

        resp = self.__do_delete(post_resp.json['id'], expect_errors=True)
        expected_msg = ('User "%s" doesn\'t have required permission "%s" on resource "%s"' %
                        ('no_permissions', PermissionType.RULE_DELETE,
                         'rule:examples:rule1'))
        self.assertEqual(resp.status_code, httplib.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_post_get_put_delete_success(self):
        action = copy.copy(self.RULE_2)

        user_db = self.users[PermissionType.RULE_CREATE]
        self.use_user(user_db)
        post_resp = self.__do_post(action)
        self.assertEqual(post_resp.status_code, httplib.CREATED)

        action['id'] = post_resp.json['id']
        action['description'] = 'some other test description'

        user_db = self.users[PermissionType.RULE_VIEW]
        self.use_user(user_db)
        get_resp = self.__do_get_one(action['id'])
        self.assertEqual(get_resp.status_code, httplib.OK)

        user_db = self.users[PermissionType.RULE_MODIFY]
        self.use_user(user_db)
        put_resp = self.__do_put(action['id'], action)
        self.assertEqual(put_resp.status_code, httplib.OK)

        user_db = self.users[PermissionType.RULE_DELETE]
        self.use_user(user_db)
        delete_resp = self.__do_delete(action['id'])
        self.assertEqual(delete_resp.status_int, httplib.NO_CONTENT)

    def __do_get_one(self, rule_id, expect_errors=False):
        return self.app.get('/v1/rules/%s' % rule_id, expect_errors=expect_errors)

    @mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
    def __do_post(self, rule, expect_errors=False):
        return self.app.post_json('/v1/rules', rule, expect_errors=expect_errors)

    def __do_put(self, rule_id, rule, expect_errors=False):
        return self.app.put_json('/v1/rules/%s' % rule_id, rule, expect_errors=expect_errors)

    def __do_delete(self, rule_id, expect_errors=False):
        return self.app.delete('/v1/rules/%s' % rule_id, expect_errors=expect_errors)
