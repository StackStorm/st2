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
from st2common.models.db.timer import TimerDB
from st2tests.fixturesloader import FixturesLoader
from tests.base import APIControllerWithRBACTestCase

http_client = six.moves.http_client

__all__ = [
    'TimerControllerRBACTestCase'
]

FIXTURES_PACK = 'timers'
TEST_FIXTURES = {
    'triggers': ['cron1.yaml', 'date1.yaml', 'interval1.yaml', 'interval2.yaml', 'interval3.yaml']
}


class TimerControllerRBACTestCase(APIControllerWithRBACTestCase):
    fixtures_loader = FixturesLoader()

    def setUp(self):
        super(TimerControllerRBACTestCase, self).setUp()
        self.models = self.fixtures_loader.save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                                               fixtures_dict=TEST_FIXTURES)

        file_name = 'cron1.yaml'
        TimerControllerRBACTestCase.TRIGGER_1 = self.fixtures_loader.load_fixtures(
            fixtures_pack=FIXTURES_PACK,
            fixtures_dict={'triggers': [file_name]})['triggers'][file_name]

        file_name = 'date1.yaml'
        TimerControllerRBACTestCase.TRIGGER_2 = self.fixtures_loader.load_fixtures(
            fixtures_pack=FIXTURES_PACK,
            fixtures_dict={'triggers': [file_name]})['triggers'][file_name]

        file_name = 'interval1.yaml'
        TimerControllerRBACTestCase.TRIGGER_3 = self.fixtures_loader.load_fixtures(
            fixtures_pack=FIXTURES_PACK,
            fixtures_dict={'triggers': [file_name]})['triggers'][file_name]

        # Insert mock users, roles and assignments

        # Users
        user_1_db = UserDB(name='timer_list')
        user_1_db = User.add_or_update(user_1_db)
        self.users['timer_list'] = user_1_db

        user_2_db = UserDB(name='timer_view')
        user_2_db = User.add_or_update(user_2_db)
        self.users['timer_view'] = user_2_db

        # Roles
        # timer_list
        grant_db = PermissionGrantDB(resource_uid=None,
                                     resource_type=ResourceType.TIMER,
                                     permission_types=[PermissionType.TIMER_LIST])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_1_db = RoleDB(name='timer_list', permission_grants=permission_grants)
        role_1_db = Role.add_or_update(role_1_db)
        self.roles['timer_list'] = role_1_db

        # timer_View on timer 1
        trigger_db = self.models['triggers']['cron1.yaml']
        timer_uid = TimerDB(name=trigger_db.name, pack=trigger_db.pack).get_uid()
        grant_db = PermissionGrantDB(resource_uid=timer_uid,
                                     resource_type=ResourceType.TIMER,
                                     permission_types=[PermissionType.TIMER_VIEW])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_1_db = RoleDB(name='timer_view', permission_grants=permission_grants)
        role_1_db = Role.add_or_update(role_1_db)
        self.roles['timer_view'] = role_1_db

        # Role assignments
        role_assignment_db = UserRoleAssignmentDB(
            user=self.users['timer_list'].name,
            role=self.roles['timer_list'].name,
            source='assignments/%s.yaml' % self.users['timer_list'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        role_assignment_db = UserRoleAssignmentDB(
            user=self.users['timer_view'].name,
            role=self.roles['timer_view'].name,
            source='assignments/%s.yaml' % self.users['timer_view'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

    def test_get_all_no_permissions(self):
        user_db = self.users['no_permissions']
        self.use_user(user_db)

        resp = self.app.get('/v1/timers', expect_errors=True)
        expected_msg = ('User "no_permissions" doesn\'t have required permission "timer_list"')
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_get_one_no_permissions(self):
        user_db = self.users['no_permissions']
        self.use_user(user_db)

        trigger_db = self.models['triggers']['cron1.yaml']
        trigger_id = trigger_db.id
        timer_uid = TimerDB(name=trigger_db.name, pack=trigger_db.pack).get_uid()
        resp = self.app.get('/v1/timers/%s' % (trigger_id), expect_errors=True)
        expected_msg = ('User "no_permissions" doesn\'t have required permission "timer_view"'
                        ' on resource "%s"' % (timer_uid))
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_get_all_permission_success_get_one_no_permission_failure(self):
        user_db = self.users['timer_list']
        self.use_user(user_db)

        # timer_list permission, but no timer_view permission
        resp = self.app.get('/v1/timers')
        self.assertEqual(resp.status_code, http_client.OK)
        self.assertEqual(len(resp.json), 5)

        trigger_db = self.models['triggers']['cron1.yaml']
        trigger_id = trigger_db.id
        timer_uid = TimerDB(name=trigger_db.name, pack=trigger_db.pack).get_uid()
        resp = self.app.get('/v1/timers/%s' % (trigger_id), expect_errors=True)
        expected_msg = ('User "timer_list" doesn\'t have required permission "timer_view"'
                        ' on resource "%s"' % (timer_uid))
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_get_one_permission_success_get_all_no_permission_failure(self):
        user_db = self.users['timer_view']
        self.use_user(user_db)

        # timer_view permission, but no timer_list permission
        trigger_db = self.models['triggers']['cron1.yaml']
        trigger_id = trigger_db.id
        trigger_uid = trigger_db.get_uid()
        resp = self.app.get('/v1/timers/%s' % (trigger_id))
        self.assertEqual(resp.status_code, http_client.OK)
        self.assertEqual(resp.json['uid'], trigger_uid)

        resp = self.app.get('/v1/timers', expect_errors=True)
        expected_msg = ('User "timer_view" doesn\'t have required permission "timer_list"')
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)
