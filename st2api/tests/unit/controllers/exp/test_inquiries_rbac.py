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
from six.moves import http_client

import st2common.validators.api.action as action_validator
from st2common.models.db.auth import UserDB
from st2common.persistence.auth import User
from st2common.models.db.rbac import RoleDB
from st2common.models.db.rbac import UserRoleAssignmentDB
from st2common.persistence.rbac import UserRoleAssignment
from st2common.persistence.rbac import Role
from st2common.transport.publishers import PoolPublisher
from tests.base import APIControllerWithRBACTestCase
from st2common.rbac.types import ResourceType
from tests.base import BaseInquiryControllerTestCase
from st2tests.fixturesloader import FixturesLoader

from st2common.rbac.types import PermissionType
from st2common.persistence.rbac import PermissionGrant
from st2common.models.db.rbac import PermissionGrantDB

from tests.unit.controllers.exp.test_inquiries import SCHEMA_DEFAULT


FIXTURES_PACK = 'generic'
TEST_FIXTURES = {
    'runners': ['inquirer.yaml', 'actionchain.yaml'],
    'actions': ['ask.yaml', 'inquiry_workflow.yaml'],
}


@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
class InquiryRBACControllerTestCase(APIControllerWithRBACTestCase,
                                    BaseInquiryControllerTestCase):

    fixtures_loader = FixturesLoader()

    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    def setUp(self):
        super(InquiryRBACControllerTestCase, self).setUp()

        self.fixtures_loader.save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                                 fixtures_dict=TEST_FIXTURES)

        # Insert mock users, roles and assignments
        assignments = {
            "user_get_db": {
                "roles": ["role_get"],
                "permissions": [PermissionType.INQUIRY_VIEW],
                "resource_type": ResourceType.INQUIRY,
                "resource_uid": 'inquiry'
            },
            "user_list_db": {
                "roles": ["role_list"],
                "permissions": [PermissionType.INQUIRY_LIST],
                "resource_type": ResourceType.INQUIRY,
                "resource_uid": 'inquiry'
            },
            "user_respond_db": {
                "roles": ["role_respond"],
                "permissions": [PermissionType.INQUIRY_RESPOND],
                "resource_type": ResourceType.INQUIRY,
                "resource_uid": 'inquiry'
            },
            "user_respond_paramtest": {
                "roles": ["role_respond_2"],
                "permissions": [PermissionType.INQUIRY_RESPOND],
                "resource_type": ResourceType.INQUIRY,
                "resource_uid": 'inquiry'
            },
            "user_respond_inherit": {
                "roles": ["role_inherit"],
                "permissions": [PermissionType.ACTION_EXECUTE],
                "resource_type": ResourceType.ACTION,
                "resource_uid": 'action:wolfpack:inquiry-workflow'
            }

        }

        # Create users
        for user in assignments.keys():
            user_db = UserDB(name=user)
            user_db = User.add_or_update(user_db)
            self.users[user] = user_db

        # Create grants and assign to roles
        for assignment_details in assignments.values():

            grant_db = PermissionGrantDB(
                permission_types=assignment_details["permissions"],
                resource_uid=assignment_details["resource_uid"],
                resource_type=assignment_details["resource_type"]
            )
            grant_db = PermissionGrant.add_or_update(grant_db)
            permission_grants = [str(grant_db.id)]

            for role in assignment_details["roles"]:
                role_db = RoleDB(name=role, permission_grants=permission_grants)
                Role.add_or_update(role_db)

        # Assign users to roles
        for user_name, assignment_details in assignments.items():
            user_db = self.users[user_name]

            for role in assignment_details['roles']:
                role_assignment_db = UserRoleAssignmentDB(
                    user=user_db.name,
                    role=role,
                    source='assignments/%s.yaml' % user_db.name)
                UserRoleAssignment.add_or_update(role_assignment_db)

        # Create Inquiry
        data = {
            'action': 'wolfpack.ask',
            'parameters': {
                "roles": [
                    'role_respond'
                ]
            }
        }

        result = {
            "schema": SCHEMA_DEFAULT,
            "roles": ['role_respond'],
            "users": [],
            "route": "",
            "ttl": 1440
        }

        result_default = {
            "schema": SCHEMA_DEFAULT,
            "roles": [],
            "users": [],
            "route": "",
            "ttl": 1440
        }

        # Use admin user for creating test objects
        user_db = self.users['admin']
        self.use_user(user_db)

        # Create workflow
        wf_data = {
            'action': 'wolfpack.inquiry-workflow'
        }
        post_resp = self.app.post_json('/v1/executions', wf_data)
        wf_id = str(post_resp.json.get('id'))

        inquiry_with_parent = {
            'action': 'wolfpack.ask',
            # 'parameters': {},
            'context': {
                "parent": {
                    'execution_id': wf_id
                }
            }
        }

        resp = self._do_create_inquiry(data, result)
        self.assertEqual(resp.status_int, http_client.OK)
        self.inquiry_id = resp.json.get('id')
        # Validated expected context for inquiries under RBAC
        expected_context = {
            'pack': 'wolfpack',
            'user': 'admin',
            'rbac': {
                'user': 'admin',
                'roles': ['admin']
            }
        }
        self.assertEqual(resp.json['context'], expected_context)

        # Create inquiry in workflow
        resp = self._do_create_inquiry(inquiry_with_parent, result_default)
        self.assertEqual(resp.status_int, http_client.OK)
        self.inquiry_inherit_id = resp.json.get('id')
        # Validated expected context for inquiries under RBAC
        expected_context = {
            'pack': 'wolfpack',
            'parent': {
                'execution_id': wf_id
            },
            'user': 'admin',
            'rbac': {
                'user': 'admin',
                'roles': ['admin']
            }
        }
        self.assertEqual(resp.json['context'], expected_context)

    def tearDown(self):
        super(InquiryRBACControllerTestCase, self).tearDown()

    def test_get_user(self):
        """Test API with RBAC inquiry 'get' permissions
        """

        # User with get permissions should succeed
        self.use_user(self.users['user_get_db'])
        resp = self._do_get_one(self.inquiry_id)
        self.assertEqual(resp.status_int, http_client.OK)

        # User with list permissions should not succeed
        self.use_user(self.users['user_list_db'])
        resp = self._do_get_one(self.inquiry_id, expect_errors=True)
        self.assertEqual(resp.status_int, http_client.FORBIDDEN)

    def test_list_user(self):
        """Test API with RBAC inquiry 'list' permissions
        """

        # User with list permissions should succeed
        self.use_user(self.users['user_list_db'])
        resp = self._do_get_all()
        self.assertEqual(resp.status_int, http_client.OK)

        # User with get permissions should not succeed
        self.use_user(self.users['user_get_db'])
        resp = self._do_get_all(expect_errors=True)
        self.assertEqual(resp.status_int, http_client.FORBIDDEN)

    def test_respond_user(self):
        """Test API with RBAC inquiry 'respond' permissions
        """

        response = {"continue": True}

        # User with list permissions should not succeed
        self.use_user(self.users['user_list_db'])
        resp = self._do_respond(self.inquiry_id, response, expect_errors=True)
        self.assertEqual(resp.status_int, http_client.FORBIDDEN)

        # User with respond permissions should succeed
        self.use_user(self.users['user_respond_db'])
        resp = self._do_respond(self.inquiry_id, response)
        self.assertEqual(resp.status_int, http_client.OK)

    def test_inquiry_roles_parameter(self):
        """Tests per-inquiry permissions enforced outside of RBAC

        These are permissions enforced by the PUT endpoint itself,
        based on the "roles" inquirer parameter
        """
        response = {"continue": True}

        # user_respond_paramtest has the INQUIRY_RESPOND permission,
        # but does not belong to a role that is in the "roles" parameter
        # for this Inquiry, so it is blocked.
        self.use_user(self.users['user_respond_paramtest'])
        resp = self._do_respond(self.inquiry_id, response, expect_errors=True)
        self.assertEqual(resp.status_int, http_client.FORBIDDEN)

        # User with respond permissions should succeed
        self.use_user(self.users['user_respond_db'])
        resp = self._do_respond(self.inquiry_id, response)
        self.assertEqual(resp.status_int, http_client.OK)

    @mock.patch('st2api.controllers.exp.inquiries.action_service')
    def test_inquiry_roles_inherit(self, mock_action_service):
        """Tests action_execute -> inquiry_respond permission inheritance

        Mocked out action_service because, since this inquiry has a parent,
        a pause will be attempted, and we don't care to test for that here.
        """

        # user_respond_inherit user doesn't have any inquiry permissions at all.
        # yet, since they are permitted to execute a workflow that contains an inquiry,
        # the user is still allowed to respond to that inquiry.
        self.use_user(self.users['user_respond_inherit'])
        resp = self._do_respond(self.inquiry_inherit_id, {"continue": True})
        self.assertEqual(resp.status_int, http_client.OK)
