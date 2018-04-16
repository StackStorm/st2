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
from st2common.constants import action as action_constants
from st2common.rbac.types import PermissionType
from st2common.rbac.types import ResourceType
from st2common.persistence.auth import User
from st2common.persistence.rbac import Role
from st2common.persistence.rbac import UserRoleAssignment
from st2common.persistence.rbac import PermissionGrant
from st2common.persistence.action import Action
from st2common.persistence.execution import ActionExecution
from st2common.models.db.auth import UserDB
from st2common.models.db.rbac import RoleDB
from st2common.models.db.rbac import UserRoleAssignmentDB
from st2common.models.db.rbac import PermissionGrantDB
from st2common.models.db.action import ActionDB
from st2common.models.db.execution import ActionExecutionDB
from st2common.rbac.resolvers import InquiryPermissionsResolver
from tests.unit.test_rbac_resolvers import BasePermissionsResolverTestCase

__all__ = [
    'InquiryPermissionsResolverTestCase'
]


class InquiryPermissionsResolverTestCase(BasePermissionsResolverTestCase):
    def setUp(self):
        super(InquiryPermissionsResolverTestCase, self).setUp()

        # Create some mock users
        user_1_db = UserDB(name='custom_role_inquiry_list_grant')
        user_1_db = User.add_or_update(user_1_db)
        self.users['custom_role_inquiry_list_grant'] = user_1_db

        user_2_db = UserDB(name='custom_role_inquiry_view_grant')
        user_2_db = User.add_or_update(user_2_db)
        self.users['custom_role_inquiry_view_grant'] = user_2_db

        user_3_db = UserDB(name='custom_role_inquiry_respond_grant')
        user_3_db = User.add_or_update(user_3_db)
        self.users['custom_role_inquiry_respond_grant'] = user_3_db

        user_4_db = UserDB(name='custom_role_inquiry_all_grant')
        user_4_db = User.add_or_update(user_4_db)
        self.users['custom_role_inquiry_all_grant'] = user_4_db

        user_5_db = UserDB(name='custom_role_inquiry_inherit')
        user_5_db = User.add_or_update(user_5_db)
        self.users['custom_role_inquiry_inherit'] = user_5_db

        # Create a workflow for testing inheritance of action_execute permission
        # to inquiry_respond permission
        wf_db = ActionDB(pack='examples', name='mistral-ask-basic', entry_point='',
                         runner_type={'name': 'mistral-v2'})
        wf_db = Action.add_or_update(wf_db)
        self.resources['wf'] = wf_db
        runner = {'name': 'mistral-v2'}
        liveaction = {'action': 'examples.mistral-ask-basic'}
        status = action_constants.LIVEACTION_STATUS_PAUSED

        # Spawn workflow
        action = {'uid': wf_db.get_uid(), 'pack': 'examples'}
        wf_exc_db = ActionExecutionDB(action=action, runner=runner, liveaction=liveaction,
                                      status=status)
        wf_exc_db = ActionExecution.add_or_update(wf_exc_db)

        # Create an Inquiry on which permissions can be granted
        action_1_db = ActionDB(pack='core', name='ask', entry_point='',
                               runner_type={'name': 'inquirer'})
        action_1_db = Action.add_or_update(action_1_db)
        self.resources['action_1'] = action_1_db
        runner = {'name': 'inquirer'}
        liveaction = {'action': 'core.ask'}
        status = action_constants.LIVEACTION_STATUS_PENDING

        # For now, Inquiries are "borrowing" the ActionExecutionDB model,
        # so we have to test with that model
        action = {'uid': action_1_db.get_uid(), 'pack': 'core'}
        inquiry_1_db = ActionExecutionDB(action=action, runner=runner, liveaction=liveaction,
                                         status=status)

        # A separate inquiry that has a parent (so we can test workflow permission inheritance)
        inquiry_2_db = ActionExecutionDB(action=action, runner=runner, liveaction=liveaction,
                                         status=status, parent=str(wf_exc_db.id))

        # A bit gross, but it's what we have to do since Inquiries
        # don't yet have their own data model
        def get_uid():
            return "inquiry"

        inquiry_1_db.get_uid = get_uid
        inquiry_2_db.get_uid = get_uid

        inquiry_1_db = ActionExecution.add_or_update(inquiry_1_db)
        inquiry_2_db = ActionExecution.add_or_update(inquiry_2_db)
        self.resources['inquiry_1'] = inquiry_1_db
        self.resources['inquiry_2'] = inquiry_2_db

        ############################################################
        # Create some mock roles with associated permission grants #
        ############################################################

        # Custom role - "inquiry_list" grant
        grant_db = PermissionGrantDB(resource_uid=self.resources['inquiry_1'].get_uid(),
                                     resource_type=ResourceType.INQUIRY,
                                     permission_types=[PermissionType.INQUIRY_LIST])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_db = RoleDB(name='custom_role_inquiry_list_grant',
                         permission_grants=permission_grants)
        role_db = Role.add_or_update(role_db)
        self.roles['custom_role_inquiry_list_grant'] = role_db

        # Custom role - "inquiry_view" grant
        grant_db = PermissionGrantDB(resource_uid=self.resources['inquiry_1'].get_uid(),
                                     resource_type=ResourceType.INQUIRY,
                                     permission_types=[PermissionType.INQUIRY_VIEW])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_db = RoleDB(name='custom_role_inquiry_view_grant',
                         permission_grants=permission_grants)
        role_db = Role.add_or_update(role_db)
        self.roles['custom_role_inquiry_view_grant'] = role_db

        # Custom role - "inquiry_respond" grant
        grant_db = PermissionGrantDB(resource_uid=self.resources['inquiry_1'].get_uid(),
                                     resource_type=ResourceType.INQUIRY,
                                     permission_types=[PermissionType.INQUIRY_RESPOND])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_db = RoleDB(name='custom_role_inquiry_respond_grant',
                         permission_grants=permission_grants)
        role_db = Role.add_or_update(role_db)
        self.roles['custom_role_inquiry_respond_grant'] = role_db

        # Custom role - "inquiry_all" grant
        grant_db = PermissionGrantDB(resource_uid=self.resources['inquiry_1'].get_uid(),
                                     resource_type=ResourceType.INQUIRY,
                                     permission_types=[PermissionType.INQUIRY_ALL])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_db = RoleDB(name='custom_role_inquiry_all_grant',
                         permission_grants=permission_grants)
        role_db = Role.add_or_update(role_db)
        self.roles['custom_role_inquiry_all_grant'] = role_db

        # Custom role - inheritance grant
        grant_db = PermissionGrantDB(resource_uid=self.resources['wf'].get_uid(),
                                     resource_type=ResourceType.ACTION,
                                     permission_types=[PermissionType.ACTION_EXECUTE])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_db = RoleDB(name='custom_role_inquiry_inherit',
                         permission_grants=permission_grants)
        role_db = Role.add_or_update(role_db)
        self.roles['custom_role_inquiry_inherit'] = role_db

        #####################################
        # Create some mock role assignments #
        #####################################

        user_db = self.users['custom_role_inquiry_list_grant']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['custom_role_inquiry_list_grant'].name,
            source='assignments/%s.yaml' % user_db.name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        user_db = self.users['custom_role_inquiry_view_grant']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['custom_role_inquiry_view_grant'].name,
            source='assignments/%s.yaml' % user_db.name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        user_db = self.users['custom_role_inquiry_respond_grant']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['custom_role_inquiry_respond_grant'].name,
            source='assignments/%s.yaml' % user_db.name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        user_db = self.users['custom_role_inquiry_all_grant']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['custom_role_inquiry_all_grant'].name,
            source='assignments/%s.yaml' % user_db.name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        user_db = self.users['custom_role_inquiry_inherit']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['custom_role_inquiry_inherit'].name,
            source='assignments/%s.yaml' % user_db.name)
        UserRoleAssignment.add_or_update(role_assignment_db)

    def test_user_has_permission(self):
        resolver = InquiryPermissionsResolver()

        # Admin user, should always return true
        user_db = self.users['admin']
        self.assertUserHasPermission(resolver=resolver,
                                     user_db=user_db,
                                     permission_type=PermissionType.INQUIRY_LIST)

        # Observer, should always return true for VIEW permissions
        user_db = self.users['observer']
        self.assertUserHasPermission(resolver=resolver,
                                     user_db=user_db,
                                     permission_type=PermissionType.INQUIRY_LIST)

        # No roles, should return false for everything
        user_db = self.users['no_roles']
        self.assertUserDoesntHavePermission(resolver=resolver,
                                            user_db=user_db,
                                            permission_type=PermissionType.INQUIRY_LIST)

        # Custom role with no permission grants, should return false for everything
        user_db = self.users['1_custom_role_no_permissions']
        self.assertUserDoesntHavePermission(resolver=resolver,
                                            user_db=user_db,
                                            permission_type=PermissionType.INQUIRY_LIST)

        # list user should be able to list
        user_db = self.users['custom_role_inquiry_list_grant']
        self.assertUserHasPermission(resolver=resolver,
                                     user_db=user_db,
                                     permission_type=PermissionType.INQUIRY_LIST)

        # view user shouldn't be able to list
        user_db = self.users['custom_role_inquiry_view_grant']
        self.assertUserDoesntHavePermission(resolver=resolver,
                                            user_db=user_db,
                                            permission_type=PermissionType.INQUIRY_LIST)

    def test_user_has_resource_db_permission(self):
        resolver = InquiryPermissionsResolver()

        all_permission_types = PermissionType.get_valid_permissions_for_resource_type(
            ResourceType.INQUIRY)
        all_permission_types.remove(PermissionType.INQUIRY_LIST)

        # Admin user, should always return true
        user_db = self.users['admin']
        self.assertUserHasResourceDbPermissions(
            resolver=resolver,
            user_db=user_db,
            resource_db=self.resources['inquiry_1'],
            permission_types=all_permission_types)

        # Observer, should always return true for VIEW permission
        user_db = self.users['observer']
        self.assertUserHasResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=self.resources['inquiry_1'],
            permission_type=PermissionType.INQUIRY_VIEW)

        self.assertUserDoesntHaveResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=self.resources['inquiry_1'],
            permission_type=PermissionType.INQUIRY_RESPOND)
        self.assertUserDoesntHaveResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=self.resources['inquiry_1'],
            permission_type=PermissionType.INQUIRY_ALL)

        # No roles, should return false for everything
        user_db = self.users['no_roles']
        self.assertUserDoesntHaveResourceDbPermissions(
            resolver=resolver,
            user_db=user_db,
            resource_db=self.resources['inquiry_1'],
            permission_types=all_permission_types)

        # Custom role with no permission grants, should return false for everything
        user_db = self.users['1_custom_role_no_permissions']
        self.assertUserDoesntHaveResourceDbPermissions(
            resolver=resolver,
            user_db=user_db,
            resource_db=self.resources['inquiry_1'],
            permission_types=all_permission_types)

        # View user should be able to view
        user_db = self.users['custom_role_inquiry_view_grant']
        self.assertUserHasResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=self.resources['inquiry_1'],
            permission_type=PermissionType.INQUIRY_VIEW)

        # Respond user should be able to respond
        user_db = self.users['custom_role_inquiry_respond_grant']
        self.assertUserHasResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=self.resources['inquiry_1'],
            permission_type=PermissionType.INQUIRY_RESPOND)

        # ALL user should have all db perms
        user_db = self.users['custom_role_inquiry_all_grant']
        self.assertUserHasResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=self.resources['inquiry_1'],
            permission_type=PermissionType.INQUIRY_ALL)

        # Now to test inheritance from action_execution for parent workflow.
        # We still have to pass in INQUIRY_RESPOND to permission_type here to keep the resolver
        # enum assert happy, but we haven't granted INQUIRY_RESPOND to this role, proving
        # that the effective permission is inherited.
        user_db = self.users['custom_role_inquiry_inherit']
        self.assertUserHasResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=self.resources['inquiry_2'],
            permission_type=PermissionType.INQUIRY_RESPOND)
