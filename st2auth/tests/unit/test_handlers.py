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

import base64

import mock
import eventlet
from oslo_config import cfg

from st2tests.base import CleanDbTestCase
import st2auth.handlers as handlers
from st2auth.backends.base import BaseAuthenticationBackend
from st2common.models.db.auth import UserDB
from st2common.persistence.auth import User
from st2common.services.rbac import get_roles_for_user
from st2common.services.rbac import create_role
from st2common.services.rbac import assign_role_to_user
from st2common.services.rbac import create_group_to_role_map
from st2common.rbac.syncer import RBACRemoteGroupToRoleSyncer
from st2common.router import exc


# auser:apassword in b64
DUMMY_CREDS = 'YXVzZXI6YXBhc3N3b3Jk'


class MockAuthBackend(BaseAuthenticationBackend):
    groups = []

    def authenticate(self, username, password):
        return ((username == 'auser' and password == 'apassword') or
                (username == 'username' and password == 'password:password'))

    def get_user(self, username):
        return username

    def get_user_groups(self, username):
        return self.groups


class MockRequest():
    def __init__(self, ttl):
        self.ttl = ttl

    user = None
    ttl = None
    impersonate_user = None
    nickname_origin = None


def get_mock_backend(name):
    return MockAuthBackend()


@mock.patch('st2auth.handlers.get_auth_backend_instance', get_mock_backend)
class HandlerTestCase(CleanDbTestCase):
    def setUp(self):
        super(HandlerTestCase, self).setUp()

        cfg.CONF.auth.backend = 'mock'

        self.users = {}
        self.roles = {}
        self.role_assignments = {}

        # Insert some mock users
        user_1_db = UserDB(name='auser')
        user_1_db = User.add_or_update(user_1_db)
        self.users['user_1'] = user_1_db

        user_2_db = UserDB(name='buser')
        user_2_db = User.add_or_update(user_2_db)
        self.users['user_2'] = user_2_db

        # Insert mock local role assignments
        role_db = create_role(name='mock_local_role_1')
        user_db = self.users['user_1']
        source = 'assignments/%s.yaml' % user_db.name
        role_assignment_db_1 = assign_role_to_user(
            role_db=role_db, user_db=user_db, source=source, is_remote=False)

        self.roles['mock_local_role_1'] = role_db
        self.role_assignments['assignment_1'] = role_assignment_db_1

        role_db = create_role(name='mock_local_role_2')
        user_db = self.users['user_1']
        source = 'assignments/%s.yaml' % user_db.name
        role_assignment_db_2 = assign_role_to_user(
            role_db=role_db, user_db=user_db, source=source, is_remote=False)

        self.roles['mock_local_role_2'] = role_db
        self.role_assignments['assignment_2'] = role_assignment_db_2

        role_db = create_role(name='mock_role_3')
        self.roles['mock_role_3'] = role_db

        role_db = create_role(name='mock_role_4')
        self.roles['mock_role_4'] = role_db

        role_db = create_role(name='mock_role_5')
        self.roles['mock_role_5'] = role_db

    def test_proxy_handler(self):
        h = handlers.ProxyAuthHandler()
        request = {}
        token = h.handle_auth(
            request, headers={}, remote_addr=None,
            remote_user='test_proxy_handler')
        self.assertEqual(token.user, 'test_proxy_handler')

    def test_standalone_bad_auth_type(self):
        h = handlers.StandaloneAuthHandler()
        request = {}

        with self.assertRaises(exc.HTTPUnauthorized):
            h.handle_auth(
                request, headers={}, remote_addr=None,
                remote_user=None, authorization=('complex', DUMMY_CREDS))

    def test_standalone_no_auth(self):
        h = handlers.StandaloneAuthHandler()
        request = {}

        with self.assertRaises(exc.HTTPUnauthorized):
            h.handle_auth(
                request, headers={}, remote_addr=None,
                remote_user=None, authorization=None)

    def test_standalone_bad_auth_value(self):
        h = handlers.StandaloneAuthHandler()
        request = {}

        with self.assertRaises(exc.HTTPUnauthorized):
            h.handle_auth(
                request, headers={}, remote_addr=None,
                remote_user=None, authorization=('basic', 'gobblegobble'))

    def test_standalone_handler(self):
        h = handlers.StandaloneAuthHandler()
        request = {}

        token = h.handle_auth(
            request, headers={}, remote_addr=None,
            remote_user=None, authorization=('basic', DUMMY_CREDS))
        self.assertEqual(token.user, 'auser')

    def test_standalone_handler_ttl(self):
        h = handlers.StandaloneAuthHandler()

        token1 = h.handle_auth(
            MockRequest(23), headers={}, remote_addr=None,
            remote_user=None, authorization=('basic', DUMMY_CREDS))
        token2 = h.handle_auth(
            MockRequest(2300), headers={}, remote_addr=None,
            remote_user=None, authorization=('basic', DUMMY_CREDS))
        self.assertEqual(token1.user, 'auser')
        self.assertNotEqual(token1.expiry, token2.expiry)

    @mock.patch.object(
        User, 'get_by_name',
        mock.MagicMock(return_value=UserDB(name='auser')))
    def test_standalone_for_user_not_service(self):
        h = handlers.StandaloneAuthHandler()
        request = MockRequest(60)
        request.user = 'anotheruser'

        with self.assertRaises(exc.HTTPBadRequest):
            h.handle_auth(
                request, headers={}, remote_addr=None,
                remote_user=None, authorization=('basic', DUMMY_CREDS))

    @mock.patch.object(
        User, 'get_by_name',
        mock.MagicMock(return_value=UserDB(name='auser', is_service=True)))
    def test_standalone_for_user_service(self):
        h = handlers.StandaloneAuthHandler()
        request = MockRequest(60)
        request.user = 'anotheruser'

        token = h.handle_auth(
            request, headers={}, remote_addr=None,
            remote_user=None, authorization=('basic', DUMMY_CREDS))
        self.assertEqual(token.user, 'anotheruser')

    def test_standalone_for_user_not_found(self):
        h = handlers.StandaloneAuthHandler()
        request = MockRequest(60)
        request.user = 'anotheruser'

        with self.assertRaises(exc.HTTPBadRequest):
            h.handle_auth(
                request, headers={}, remote_addr=None,
                remote_user=None, authorization=('basic', DUMMY_CREDS))

    def test_standalone_impersonate_user_not_found(self):
        h = handlers.StandaloneAuthHandler()
        request = MockRequest(60)
        request.impersonate_user = 'anotheruser'

        with self.assertRaises(exc.HTTPBadRequest):
            h.handle_auth(
                request, headers={}, remote_addr=None,
                remote_user=None, authorization=('basic', DUMMY_CREDS))

    @mock.patch.object(
        User, 'get_by_name',
        mock.MagicMock(return_value=UserDB(name='auser', is_service=True)))
    @mock.patch.object(
        User, 'get_by_nickname',
        mock.MagicMock(return_value=UserDB(name='anotheruser', is_service=True)))
    def test_standalone_impersonate_user_with_nick_origin(self):
        h = handlers.StandaloneAuthHandler()
        request = MockRequest(60)
        request.impersonate_user = 'anotheruser'
        request.nickname_origin = 'slack'

        token = h.handle_auth(
            request, headers={}, remote_addr=None,
            remote_user=None, authorization=('basic', DUMMY_CREDS))
        self.assertEqual(token.user, 'anotheruser')

    def test_standalone_impersonate_user_no_origin(self):
        h = handlers.StandaloneAuthHandler()
        request = MockRequest(60)
        request.impersonate_user = '@anotheruser'

        with self.assertRaises(exc.HTTPBadRequest):
            h.handle_auth(
                request, headers={}, remote_addr=None,
                remote_user=None, authorization=('basic', DUMMY_CREDS))

    def test_password_contains_colon(self):
        h = handlers.StandaloneAuthHandler()
        request = MockRequest(60)

        authorization = ('Basic', base64.b64encode(b'username:password:password'))
        token = h.handle_auth(
            request, headers={}, remote_addr=None,
            remote_user=None, authorization=authorization)
        self.assertEqual(token.user, 'username')

    def test_group_to_role_sync_is_performed_on_successful_auth_no_groups_returned(self):
        # Enable group sync
        cfg.CONF.set_override(group='rbac', name='sync_remote_groups', override=True)
        cfg.CONF.set_override(group='rbac', name='sync_remote_groups', override=True)

        user_db = self.users['user_1']
        h = handlers.StandaloneAuthHandler()
        request = {}

        # Verify initial state
        role_dbs = get_roles_for_user(user_db=user_db, include_remote=True)
        self.assertEqual(len(role_dbs), 2)
        self.assertEqual(role_dbs[0], self.roles['mock_local_role_1'])
        self.assertEqual(role_dbs[1], self.roles['mock_local_role_2'])

        # No groups configured should return early
        h._auth_backend.groups = []

        token = h.handle_auth(request, headers={}, remote_addr=None, remote_user=None,
                              authorization=('basic', DUMMY_CREDS))
        self.assertEqual(token.user, 'auser')

        # Verify nothing has changed
        role_dbs = get_roles_for_user(user_db=user_db, include_remote=True)
        self.assertEqual(len(role_dbs), 2)
        self.assertEqual(role_dbs[0], self.roles['mock_local_role_1'])
        self.assertEqual(role_dbs[1], self.roles['mock_local_role_2'])

    def test_group_to_role_sync_is_performed_on_successful_auth_single_group_no_mappings(self):
        # Enable group sync
        cfg.CONF.set_override(group='rbac', name='sync_remote_groups', override=True)
        cfg.CONF.set_override(group='rbac', name='sync_remote_groups', override=True)

        user_db = self.users['user_1']
        h = handlers.StandaloneAuthHandler()
        request = {}

        # Verify initial state
        role_dbs = get_roles_for_user(user_db=user_db, include_remote=True)
        self.assertEqual(len(role_dbs), 2)
        self.assertEqual(role_dbs[0], self.roles['mock_local_role_1'])
        self.assertEqual(role_dbs[1], self.roles['mock_local_role_2'])

        # Single group configured but no group mapping in the database
        h._auth_backend.groups = [
            'CN=stormers,OU=groups,DC=stackstorm,DC=net'
        ]

        token = h.handle_auth(request, headers={}, remote_addr=None, remote_user=None,
                              authorization=('basic', DUMMY_CREDS))
        self.assertEqual(token.user, 'auser')

        # Verify nothing has changed
        role_dbs = get_roles_for_user(user_db=user_db, include_remote=True)
        self.assertEqual(len(role_dbs), 2)
        self.assertEqual(role_dbs[0], self.roles['mock_local_role_1'])
        self.assertEqual(role_dbs[1], self.roles['mock_local_role_2'])

    def test_group_to_role_sync_is_performed_on_successful_auth_with_groups_and_mappings(self):
        # Enable group sync
        cfg.CONF.set_override(group='rbac', name='sync_remote_groups', override=True)
        cfg.CONF.set_override(group='rbac', name='sync_remote_groups', override=True)

        user_db = self.users['user_1']
        h = handlers.StandaloneAuthHandler()
        request = {}

        # Single mapping, new remote assignment should be created
        create_group_to_role_map(group='CN=stormers,OU=groups,DC=stackstorm,DC=net',
                                 roles=['mock_role_3', 'mock_role_4'],
                                 source='mappings/stormers.yaml')

        # Verify initial state
        role_dbs = get_roles_for_user(user_db=user_db, include_remote=True)
        self.assertEqual(len(role_dbs), 2)
        self.assertEqual(role_dbs[0], self.roles['mock_local_role_1'])
        self.assertEqual(role_dbs[1], self.roles['mock_local_role_2'])

        h._auth_backend.groups = [
            'CN=stormers,OU=groups,DC=stackstorm,DC=net'
        ]

        token = h.handle_auth(request, headers={}, remote_addr=None, remote_user=None,
                              authorization=('basic', DUMMY_CREDS))
        self.assertEqual(token.user, 'auser')

        # Verify a new role assignments based on the group mapping has been created
        role_dbs = get_roles_for_user(user_db=user_db, include_remote=True)

        self.assertEqual(len(role_dbs), 4)
        self.assertEqual(role_dbs[0], self.roles['mock_local_role_1'])
        self.assertEqual(role_dbs[1], self.roles['mock_local_role_2'])
        self.assertEqual(role_dbs[2], self.roles['mock_role_3'])
        self.assertEqual(role_dbs[3], self.roles['mock_role_4'])

    def test_group_to_role_sync_concurrent_auth(self):
        # Verify that there is no race and group sync during concurrent auth works fine
        # Enable group sync
        cfg.CONF.set_override(group='rbac', name='sync_remote_groups', override=True)
        cfg.CONF.set_override(group='rbac', name='sync_remote_groups', override=True)

        h = handlers.StandaloneAuthHandler()
        request = {}

        def handle_auth():
            token = h.handle_auth(request, headers={}, remote_addr=None, remote_user=None,
                                  authorization=('basic', DUMMY_CREDS))
            self.assertEqual(token.user, 'auser')

        thread_pool = eventlet.GreenPool(20)

        for i in range(0, 20):
            thread_pool.spawn(handle_auth)

        thread_pool.waitall()

    @mock.patch.object(RBACRemoteGroupToRoleSyncer, 'sync',
                      mock.Mock(side_effect=Exception('throw')))
    def test_group_to_role_sync_error_non_fatal_on_succesful_auth(self):
        # Enable group sync
        cfg.CONF.set_override(group='rbac', name='sync_remote_groups', override=True)
        cfg.CONF.set_override(group='rbac', name='sync_remote_groups', override=True)

        h = handlers.StandaloneAuthHandler()
        request = {}

        h._auth_backend.groups = [
            'CN=stormers,OU=groups,DC=stackstorm,DC=net'
        ]

        # sync() method called upon successful authentication throwing should not be fatal
        token = h.handle_auth(request, headers={}, remote_addr=None, remote_user=None,
                              authorization=('basic', DUMMY_CREDS))
        self.assertEqual(token.user, 'auser')
