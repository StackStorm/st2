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

import mock

import st2common.validators.api.action as action_validator
from st2common.models.db.auth import UserDB
from st2common.persistence.auth import User
from st2common.models.db.rbac import RoleDB
from st2common.models.db.rbac import UserRoleAssignmentDB
from st2common.persistence.rbac import UserRoleAssignment
from st2common.persistence.rbac import Role
from st2common.transport.publishers import PoolPublisher
from tests.base import APIControllerWithRBACTestCase
from tests.base import BaseActionExecutionControllerTestCase
from st2tests.fixturesloader import FixturesLoader


FIXTURES_PACK = 'generic'
TEST_FIXTURES = {
    'runners': ['testrunner1.yaml'],
    'actions': ['action1.yaml', 'local.yaml']
}


@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
class ActionExecutionRBACControllerTestCase(BaseActionExecutionControllerTestCase,
                                            APIControllerWithRBACTestCase):

    fixtures_loader = FixturesLoader()

    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    def setUp(self):
        super(ActionExecutionRBACControllerTestCase, self).setUp()

        self.fixtures_loader.save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                                 fixtures_dict=TEST_FIXTURES)

        # Insert mock users, roles and assignments

        # Users
        user_1_db = UserDB(name='multiple_roles')
        user_1_db = User.add_or_update(user_1_db)
        self.users['multiple_roles'] = user_1_db

        # Roles
        roles = ['role_1', 'role_2', 'role_3']
        for role in roles:
            role_db = RoleDB(name=role)
            Role.add_or_update(role_db)

        # Role assignments
        user_db = self.users['multiple_roles']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role='admin')
        UserRoleAssignment.add_or_update(role_assignment_db)

        for role in roles:
            role_assignment_db = UserRoleAssignmentDB(
                user=user_db.name,
                role=role)
            UserRoleAssignment.add_or_update(role_assignment_db)

    def test_post_rbac_info_in_context_success(self):
        # When RBAC is enabled, additional RBAC related info should be included in action_context
        data = {
            'action': 'wolfpack.action-1',
            'parameters': {
                'actionstr': 'foo'
            }
        }

        # User with one role assignment
        user_db = self.users['admin']
        self.use_user(user_db)

        resp = self._do_post(data)
        self.assertEqual(resp.status_int, 201)

        expected_context = {
            'user': 'admin',
            'rbac': {
                'user': 'admin',
                'roles': ['admin']
            }
        }

        self.assertEqual(resp.json['context'], expected_context)

        # User with multiple role assignments
        user_db = self.users['multiple_roles']
        self.use_user(user_db)

        resp = self._do_post(data)
        self.assertEqual(resp.status_int, 201)

        expected_context = {
            'user': 'multiple_roles',
            'rbac': {
                'user': 'multiple_roles',
                'roles': ['admin', 'role_1', 'role_2', 'role_3']
            }
        }

        self.assertEqual(resp.json['context'], expected_context)
