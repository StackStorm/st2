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
import unittest

import mock
import six
from oslo_config import cfg

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
    'BaseRuleControllerRBACTestCase',
    'RuleControllerRBACTestCase'
]

FIXTURES_PACK = 'generic'
TEST_FIXTURES = {
    'runners': ['testrunner1.yaml'],
    'actions': ['action1.yaml', 'local.yaml'],
    'triggers': ['trigger1.yaml'],
    'triggertypes': ['triggertype1.yaml']
}


class BaseRuleControllerRBACTestCase(APIControllerWithRBACTestCase):
    """
    Base test class for various rule API controllers.

    Right now it's for for the following controllers:

    1) /v1/rules
    2) /v1/rules/views
    """

    fixtures_loader = FixturesLoader()
    api_endpoint = None

    @classmethod
    def setUpClass(cls):
        if cls.__name__ == 'BaseRuleControllerRBACTestCase':
            raise unittest.SkipTest('Skip base test class tests')

        super(BaseRuleControllerRBACTestCase, cls).setUpClass()

    def setUp(self):
        super(BaseRuleControllerRBACTestCase, self).setUp()
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

        file_name = 'rule_action_doesnt_exist.yaml'
        self.RULE_3 = self.fixtures_loader.load_fixtures(
            fixtures_pack=FIXTURES_PACK,
            fixtures_dict={'rules': [file_name]})['rules'][file_name]

        # Insert mock users, roles and assignments

        # Users
        user_1_db = UserDB(name='rule_create')
        user_1_db = User.add_or_update(user_1_db)
        self.users['rule_create'] = user_1_db

        user_2_db = UserDB(name='rule_create_webhook_create')
        user_2_db = User.add_or_update(user_2_db)
        self.users['rule_create_webhook_create'] = user_2_db

        user_3_db = UserDB(name='rule_create_webhook_create_core_local_execute')
        user_3_db = User.add_or_update(user_3_db)
        self.users['rule_create_webhook_create_core_local_execute'] = user_3_db

        user_4_db = UserDB(name='rule_create_1')
        user_4_db = User.add_or_update(user_4_db)
        self.users['rule_create_1'] = user_4_db

        user_5_db = UserDB(name='user_two')
        user_5_db = User.add_or_update(user_5_db)
        self.users['user_two'] = user_5_db

        user_6_db = UserDB(name='user_three')
        user_6_db = User.add_or_update(user_6_db)
        self.users['user_three'] = user_6_db

        # Roles
        # rule_create grant on parent pack
        grant_db = PermissionGrantDB(resource_uid='pack:examples',
                                     resource_type=ResourceType.PACK,
                                     permission_types=[PermissionType.RULE_CREATE])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_1_db = RoleDB(name='rule_create', permission_grants=permission_grants)
        role_1_db = Role.add_or_update(role_1_db)
        self.roles['rule_create'] = role_1_db

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

        # rule_create, rule_list, webhook_create, action_execute on parent pack
        grant_6_db = PermissionGrantDB(resource_uid='pack:examples',
                                     resource_type=ResourceType.RULE,
                                     permission_types=[PermissionType.RULE_LIST])
        grant_6_db = PermissionGrant.add_or_update(grant_6_db)

        permission_grants = [str(grant_1_db.id), str(grant_2_db.id), str(grant_3_db.id),
                             str(grant_6_db.id)]

        role_5_db = RoleDB(name='rule_create_list_webhook_create_core_local_execute',
                           permission_grants=permission_grants)
        role_5_db = Role.add_or_update(role_5_db)
        self.roles['rule_create_list_webhook_create_core_local_execute'] = role_5_db

        # rule_create grant on parent pack, webhook_create on webhook "sample", action_execute on
        # examples and wolfpack
        grant_1_db = PermissionGrantDB(resource_uid='pack:examples',
                                     resource_type=ResourceType.PACK,
                                     permission_types=[PermissionType.RULE_CREATE])
        grant_1_db = PermissionGrant.add_or_update(grant_1_db)
        grant_2_db = PermissionGrantDB(resource_uid='webhook:sample',
                                     resource_type=ResourceType.WEBHOOK,
                                     permission_types=[PermissionType.WEBHOOK_CREATE])
        grant_2_db = PermissionGrant.add_or_update(grant_2_db)
        grant_3_db = PermissionGrantDB(resource_uid='pack:wolfpack',
                                     resource_type=ResourceType.PACK,
                                     permission_types=[PermissionType.ACTION_ALL])
        grant_3_db = PermissionGrant.add_or_update(grant_3_db)
        grant_4_db = PermissionGrantDB(resource_uid=None,
                                       resource_type=ResourceType.RULE,
                                       permission_types=[PermissionType.RULE_LIST])
        grant_4_db = PermissionGrant.add_or_update(grant_4_db)
        grant_5_db = PermissionGrantDB(resource_uid='pack:examples',
                                     resource_type=ResourceType.PACK,
                                     permission_types=[PermissionType.ACTION_ALL])
        grant_5_db = PermissionGrant.add_or_update(grant_5_db)

        permission_grants = [str(grant_1_db.id), str(grant_2_db.id), str(grant_3_db.id),
                             str(grant_4_db.id), str(grant_5_db.id)]

        role_4_db = RoleDB(name='rule_create_webhook_create_action_execute',
                           permission_grants=permission_grants)
        role_4_db = Role.add_or_update(role_4_db)
        self.roles['rule_create_webhook_create_action_execute'] = role_4_db

        # Role assignments
        user_db = self.users['rule_create']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['rule_create'].name,
            source='assignments/%s.yaml' % user_db.name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        user_db = self.users['rule_create_webhook_create']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['rule_create_webhook_create'].name,
            source='assignments/%s.yaml' % user_db.name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        user_db = self.users['rule_create_webhook_create_core_local_execute']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['rule_create_webhook_create_core_local_execute'].name,
            source='assignments/%s.yaml' % user_db.name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        user_db = self.users['rule_create_1']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['rule_create_webhook_create_action_execute'].name,
            source='assignments/%s.yaml' % user_db.name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        user_db = self.users['user_two']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role='rule_create_list_webhook_create_core_local_execute',
            source='assignments/%s.yaml' % user_db.name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        user_db = self.users['user_three']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role='rule_create_list_webhook_create_core_local_execute',
            source='assignments/%s.yaml' % user_db.name)
        UserRoleAssignment.add_or_update(role_assignment_db)

    def test_get_all_respective_actions_with_permission_isolation(self):
        cfg.CONF.set_override(name='permission_isolation', override=True, group='rbac')

        rule = self.RULE_1
        result = self._insert_mock_rule_data_for_isolation_tests(rule=rule)
        self.assertEqual(len(result['admin']), 1)
        self.assertEqual(len(result['user_two']), 2)
        self.assertEqual(len(result['user_three']), 2)

        # 1. Admin can view all
        user_db = self.users['admin']
        self.use_user(user_db)

        resp = self.app.get('%s?limit=100' % (self.api_endpoint))
        self.assertEqual(len(resp.json), (1 + 2 + 2))
        self.assertEqual(resp.json[0]['context']['user'], 'admin')
        self.assertEqual(resp.json[1]['context']['user'], 'user_two')
        self.assertEqual(resp.json[2]['context']['user'], 'user_two')
        self.assertEqual(resp.json[3]['context']['user'], 'user_three')
        self.assertEqual(resp.json[4]['context']['user'], 'user_three')

        # 2. System user can view all
        user_db = self.users['system_user']
        self.use_user(user_db)

        resp = self.app.get('%s?limit=100' % (self.api_endpoint))
        self.assertEqual(len(resp.json), (1 + 2 + 2))
        self.assertEqual(resp.json[0]['context']['user'], 'admin')
        self.assertEqual(resp.json[1]['context']['user'], 'user_two')
        self.assertEqual(resp.json[2]['context']['user'], 'user_two')
        self.assertEqual(resp.json[3]['context']['user'], 'user_three')
        self.assertEqual(resp.json[4]['context']['user'], 'user_three')

        # 3. User two can only view their own
        user_db = self.users['user_two']
        self.use_user(user_db)

        resp = self.app.get('%s?limit=100' % (self.api_endpoint))
        self.assertEqual(len(resp.json), 2)
        self.assertEqual(resp.json[0]['context']['user'], 'user_two')
        self.assertEqual(resp.json[1]['context']['user'], 'user_two')

        # 4. User three can only view their own
        user_db = self.users['user_three']
        self.use_user(user_db)

        resp = self.app.get('%s?limit=100' % (self.api_endpoint))
        self.assertEqual(len(resp.json), 2)
        self.assertEqual(resp.json[0]['context']['user'], 'user_three')
        self.assertEqual(resp.json[1]['context']['user'], 'user_three')

    def test_get_one_user_resource_permission_isolation(self):
        cfg.CONF.set_override(name='permission_isolation', override=True, group='rbac')

        rule = self.RULE_1
        result = self._insert_mock_rule_data_for_isolation_tests(rule=rule)
        self.assertEqual(len(result['admin']), 1)
        self.assertEqual(len(result['user_two']), 2)
        self.assertEqual(len(result['user_three']), 2)

        # 1. Admin can view all
        user_db = self.users['admin']
        self.use_user(user_db)

        for username, rule_ids in result.items():
            for rule_id in rule_ids:
                resp = self.app.get('%s/%s' % (self.api_endpoint, rule_id))
                self.assertEqual(resp.status_code, http_client.OK)
                self.assertEqual(resp.json['id'], rule_id)
                self.assertEqual(resp.json['context']['user'], username)

        # 2. System user can view all
        user_db = self.users['system_user']
        self.use_user(user_db)

        for username, rule_ids in result.items():
            for rule_id in rule_ids:
                resp = self.app.get('%s/%s' % (self.api_endpoint, rule_id))
                self.assertEqual(resp.status_code, http_client.OK)
                self.assertEqual(resp.json['id'], rule_id)
                self.assertEqual(resp.json['context']['user'], username)

        # 3. User two can only view their own
        user_db = self.users['user_two']
        self.use_user(user_db)

        for rule_id in result['user_two']:
            resp = self.app.get('%s/%s' % (self.api_endpoint, rule_id))
            self.assertEqual(resp.status_code, http_client.OK)
            self.assertEqual(resp.json['id'], rule_id)
            self.assertEqual(resp.json['context']['user'], 'user_two')

        expected_msg = ('User "user_two" doesn\'t have access to resource "rule:.*" due to '
                        'resource permission isolation.')

        for rule_id in result['admin']:
            resp = self.app.get('%s/%s' % (self.api_endpoint, rule_id), expect_errors=True)
            self.assertEqual(resp.status_code, http_client.FORBIDDEN)
            self.assertRegexpMatches(resp.json['faultstring'], expected_msg)

        for rule_id in result['user_three']:
            resp = self.app.get('%s/%s' % (self.api_endpoint, rule_id), expect_errors=True)
            self.assertEqual(resp.status_code, http_client.FORBIDDEN)
            self.assertRegexpMatches(resp.json['faultstring'], expected_msg)

        # 4. User three can only view their own
        user_db = self.users['user_three']
        self.use_user(user_db)

        for rule_id in result['user_three']:
            resp = self.app.get('%s/%s' % (self.api_endpoint, rule_id))
            self.assertEqual(resp.status_code, http_client.OK)
            self.assertEqual(resp.json['id'], rule_id)
            self.assertEqual(resp.json['context']['user'], 'user_three')

        expected_msg = ('User "user_three" doesn\'t have access to resource "rule:.*" due to '
                        'resource permission isolation.')

        for rule_id in result['admin']:
            resp = self.app.get('%s/%s' % (self.api_endpoint, rule_id), expect_errors=True)
            self.assertEqual(resp.status_code, http_client.FORBIDDEN)
            self.assertRegexpMatches(resp.json['faultstring'], expected_msg)

        for rule_id in result['user_two']:
            resp = self.app.get('%s/%s' % (self.api_endpoint, rule_id), expect_errors=True)
            self.assertEqual(resp.status_code, http_client.FORBIDDEN)
            self.assertRegexpMatches(resp.json['faultstring'], expected_msg)

        # 5. Observer can only view their own
        user_db = self.users['observer']
        self.use_user(user_db)

        expected_msg = ('User "observer" doesn\'t have access to resource "rule:.*" due to '
                        'resource permission isolation.')

        for username, rule_ids in result.items():
            for rule_id in rule_ids:
                resp = self.app.get('%s/%s' % (self.api_endpoint, rule_id), expect_errors=True)
                self.assertEqual(resp.status_code, http_client.FORBIDDEN)
                self.assertRegexpMatches(resp.json['faultstring'], expected_msg)

    @mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
    def _do_post(self, rule):
        return self.app.post_json('/v1/rules', rule, expect_errors=True)

    def _insert_mock_rule_data_for_isolation_tests(self, rule):
        data = copy.copy(rule)

        result = {
            'admin': [],
            'user_two': [],
            'user_three': []
        }

        # User with admin role assignment
        user_db = self.users['admin']
        self.use_user(user_db)

        data['name'] += '1'
        resp = self._do_post(data)
        self.assertEqual(resp.status_code, http_client.CREATED)
        result['admin'].append(resp.json['id'])

        # User two
        user_db = self.users['user_two']
        self.use_user(user_db)

        data['name'] += '2'
        resp = self._do_post(data)
        self.assertEqual(resp.status_code, http_client.CREATED)
        result['user_two'].append(resp.json['id'])

        data['name'] += '3'
        resp = self._do_post(data)
        self.assertEqual(resp.status_code, http_client.CREATED)
        result['user_two'].append(resp.json['id'])

        # User two
        user_db = self.users['user_three']
        self.use_user(user_db)

        data['name'] += '4'
        resp = self._do_post(data)
        self.assertEqual(resp.status_code, http_client.CREATED)
        result['user_three'].append(resp.json['id'])

        data['name'] += '5'
        resp = self._do_post(data)
        self.assertEqual(resp.status_code, http_client.CREATED)
        result['user_three'].append(resp.json['id'])

        return result


class RuleControllerRBACTestCase(BaseRuleControllerRBACTestCase):
    api_endpoint = '/v1/rules'

    def test_post_webhook_trigger_no_trigger_and_action_permission(self):
        # Test a scenario when user selects a webhook trigger, but only has "rule_create"
        # permission
        user_db = self.users['rule_create']
        self.use_user(user_db)

        resp = self._do_post(self.RULE_1)
        expected_msg = ('User "rule_create" doesn\'t have required permission (webhook_create) '
                        'to use trigger core.st2.webhook')
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_post_user_has_no_permission_on_action_which_doesnt_exist_in_db(self):
        # User has rule_create, but no action_execute on the action which doesn't exist in the db
        user_db = self.users['rule_create_webhook_create']
        self.use_user(user_db)

        resp = self._do_post(self.RULE_3)
        expected_msg = ('User "rule_create_webhook_create" doesn\'t have required (action_execute)'
                        ' permission to use action wolfpack.action-doesnt-exist-woo')
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_post_no_webhook_trigger(self):
        # Test a scenario when user with only "rule_create" permission selects a non-webhook
        # trigger for which we don't perform any permission checking right now
        user_db = self.users['rule_create']
        self.use_user(user_db)

        resp = self._do_post(self.RULE_2)
        expected_msg = ('User "rule_create" doesn\'t have required (action_execute) permission '
                        'to use action wolfpack.action-1')
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_post_webhook_trigger_webhook_create_permission_no_action_permission(self):
        # Test a scenario where user with "rule_create" and "webhook_create" selects a webhook
        # trigger and core.local action
        user_db = self.users['rule_create_webhook_create']
        self.use_user(user_db)

        resp = self._do_post(self.RULE_1)
        expected_msg = ('User "rule_create_webhook_create" doesn\'t have required '
                        '(action_execute) permission to use action core.local')
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_post_action_webhook_trigger_webhook_create_and_action_execute_permission(self):
        # Test a scenario where user selects a webhook trigger and has all the required permissions
        user_db = self.users['rule_create_webhook_create_core_local_execute']
        self.use_user(user_db)

        resp = self._do_post(self.RULE_1)
        self.assertEqual(resp.status_code, http_client.CREATED)

    def test_get_all_limit_minus_one(self):
        user_db = self.users['observer']
        self.use_user(user_db)

        resp = self.app.get('/v1/rules?limit=-1', expect_errors=True)
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)

        user_db = self.users['admin']
        self.use_user(user_db)

        resp = self.app.get('/v1/rules?limit=-1')
        self.assertEqual(resp.status_code, http_client.OK)
