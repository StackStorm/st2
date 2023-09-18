# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import

import base64

import mock
from oslo_config import cfg

from st2tests.base import CleanDbTestCase
import st2auth.handlers as handlers
from st2common.models.db.auth import UserDB
from st2common.persistence.auth import User
from st2common.router import exc

from st2tests.mocks.auth import DUMMY_CREDS
from st2tests.mocks.auth import MockRequest
from st2tests.mocks.auth import get_mock_backend

from st2common.persistence.rbac import UserRoleAssignment
from st2common.models.db.rbac import GroupToRoleMappingDB, RoleDB


__all__ = ["AuthHandlerTestCase"]

from st2common.router import GenericRequestParam

MOCK_USER = "test_proxy_handler"


@mock.patch("st2auth.handlers.get_auth_backend_instance", get_mock_backend)
class ProxyHandlerRBACAndGroupsTestCase(CleanDbTestCase):
    def _assert_roles_len(self, user, total):
        user_roles = UserRoleAssignment.get_all(user=user)
        self.assertEqual(len(user_roles), total)
        return user_roles

    def setUp(self):
        super(ProxyHandlerRBACAndGroupsTestCase, self).setUp()

        cfg.CONF.auth.backend = "mock"

        # Create test roles
        RoleDB(name="role-1").save()
        RoleDB(name="role-2").save()

        # Create tsts mappings
        GroupToRoleMappingDB(
            group="group-1", roles=["role-1"], source="test", enabled=True
        ).save()

        GroupToRoleMappingDB(
            group="group-2", roles=["role-2"], source="test", enabled=True
        ).save()

        cfg.CONF.set_override(name="enable", group="rbac", override=False)
        cfg.CONF.set_override(name="backend", group="rbac", override="noop")

    def test_proxy_handler_no_groups_no_rbac(self):
        h = handlers.ProxyAuthHandler()
        request = {}
        token = h.handle_auth(
            request, headers={}, remote_addr=None, remote_user=MOCK_USER
        )
        self._assert_roles_len(token.user, 0)
        self.assertEqual(token.user, MOCK_USER)

    def test_proxy_handler_with_groups_and_rbac_disabled(self):

        h = handlers.ProxyAuthHandler()

        request = GenericRequestParam(groups=["group-1", "group-2"])
        token = h.handle_auth(
            request, headers={}, remote_addr=None, remote_user=MOCK_USER
        )
        self._assert_roles_len(token.user, 0)

        self.assertEqual(token.user, MOCK_USER)

    def test_proxy_handler_with_groups_and_rbac_enabled(self):

        cfg.CONF.set_override(name="enable", group="rbac", override=True)
        cfg.CONF.set_override(name="backend", group="rbac", override="default")

        h = handlers.ProxyAuthHandler()

        request = GenericRequestParam(groups=["group-1", "group-2"])
        token = h.handle_auth(
            request, headers={}, remote_addr=None, remote_user=MOCK_USER
        )

        self.assertEqual(token.user, MOCK_USER)
        user_roles = self._assert_roles_len(token.user, 2)
        self.assertEqual(user_roles[0].role, "role-1")
        self.assertEqual(user_roles[1].role, "role-2")

    def test_proxy_handler_no_groups_and_rbac_enabled_with_no_prior_roles(self):

        cfg.CONF.set_override(name="enable", group="rbac", override=True)
        cfg.CONF.set_override(name="backend", group="rbac", override="default")

        h = handlers.ProxyAuthHandler()

        request = GenericRequestParam(groups=[])
        token = h.handle_auth(
            request, headers={}, remote_addr=None, remote_user=MOCK_USER
        )
        user_roles = self._assert_roles_len(token.user, 0)

        self.assertEqual(token.user, MOCK_USER)
        self.assertEqual(len(user_roles), 0)

    def test_proxy_handler_no_groups_and_rbac_enabled_with_prior_roles(self):

        self.test_proxy_handler_with_groups_and_rbac_enabled()
        self._assert_roles_len(MOCK_USER, 2)

        cfg.CONF.set_override(name="enable", group="rbac", override=True)
        cfg.CONF.set_override(name="backend", group="rbac", override="default")

        h = handlers.ProxyAuthHandler()

        request = GenericRequestParam(groups=[])
        token = h.handle_auth(
            request, headers={}, remote_addr=None, remote_user=MOCK_USER
        )
        user_roles = UserRoleAssignment.get_all(user=token.user)

        self.assertEqual(token.user, MOCK_USER)
        self.assertEqual(len(user_roles), 0)


@mock.patch("st2auth.handlers.get_auth_backend_instance", get_mock_backend)
class AuthHandlerTestCase(CleanDbTestCase):
    def setUp(self):
        super(AuthHandlerTestCase, self).setUp()

        cfg.CONF.auth.backend = "mock"

    def test_standalone_bad_auth_type(self):
        h = handlers.StandaloneAuthHandler()
        request = {}

        with self.assertRaises(exc.HTTPUnauthorized):
            h.handle_auth(
                request,
                headers={},
                remote_addr=None,
                remote_user=None,
                authorization=("complex", DUMMY_CREDS),
            )

    def test_standalone_no_auth(self):
        h = handlers.StandaloneAuthHandler()
        request = {}

        with self.assertRaises(exc.HTTPUnauthorized):
            h.handle_auth(
                request,
                headers={},
                remote_addr=None,
                remote_user=None,
                authorization=None,
            )

    def test_standalone_bad_auth_value(self):
        h = handlers.StandaloneAuthHandler()
        request = {}

        with self.assertRaises(exc.HTTPUnauthorized):
            h.handle_auth(
                request,
                headers={},
                remote_addr=None,
                remote_user=None,
                authorization=("basic", "gobblegobble"),
            )

    def test_standalone_handler(self):
        h = handlers.StandaloneAuthHandler()
        request = {}

        token = h.handle_auth(
            request,
            headers={},
            remote_addr=None,
            remote_user=None,
            authorization=("basic", DUMMY_CREDS),
        )
        self.assertEqual(token.user, "auser")

    def test_standalone_handler_ttl(self):
        h = handlers.StandaloneAuthHandler()

        token1 = h.handle_auth(
            MockRequest(23),
            headers={},
            remote_addr=None,
            remote_user=None,
            authorization=("basic", DUMMY_CREDS),
        )
        token2 = h.handle_auth(
            MockRequest(2300),
            headers={},
            remote_addr=None,
            remote_user=None,
            authorization=("basic", DUMMY_CREDS),
        )
        self.assertEqual(token1.user, "auser")
        self.assertNotEqual(token1.expiry, token2.expiry)

    @mock.patch.object(
        User, "get_by_name", mock.MagicMock(return_value=UserDB(name="auser"))
    )
    def test_standalone_for_user_not_service(self):
        h = handlers.StandaloneAuthHandler()
        request = MockRequest(60)
        request.user = "anotheruser"

        with self.assertRaises(exc.HTTPBadRequest):
            h.handle_auth(
                request,
                headers={},
                remote_addr=None,
                remote_user=None,
                authorization=("basic", DUMMY_CREDS),
            )

    @mock.patch.object(
        User,
        "get_by_name",
        mock.MagicMock(return_value=UserDB(name="auser", is_service=True)),
    )
    def test_standalone_for_user_service(self):
        h = handlers.StandaloneAuthHandler()
        request = MockRequest(60)
        request.user = "anotheruser"

        token = h.handle_auth(
            request,
            headers={},
            remote_addr=None,
            remote_user=None,
            authorization=("basic", DUMMY_CREDS),
        )
        self.assertEqual(token.user, "anotheruser")

    def test_standalone_for_user_not_found(self):
        h = handlers.StandaloneAuthHandler()
        request = MockRequest(60)
        request.user = "anotheruser"

        with self.assertRaises(exc.HTTPBadRequest):
            h.handle_auth(
                request,
                headers={},
                remote_addr=None,
                remote_user=None,
                authorization=("basic", DUMMY_CREDS),
            )

    def test_standalone_impersonate_user_not_found(self):
        h = handlers.StandaloneAuthHandler()
        request = MockRequest(60)
        request.impersonate_user = "anotheruser"

        with self.assertRaises(exc.HTTPBadRequest):
            h.handle_auth(
                request,
                headers={},
                remote_addr=None,
                remote_user=None,
                authorization=("basic", DUMMY_CREDS),
            )

    @mock.patch.object(
        User,
        "get_by_name",
        mock.MagicMock(return_value=UserDB(name="auser", is_service=True)),
    )
    @mock.patch.object(
        User,
        "get_by_nickname",
        mock.MagicMock(return_value=UserDB(name="anotheruser", is_service=True)),
    )
    def test_standalone_impersonate_user_with_nick_origin(self):
        h = handlers.StandaloneAuthHandler()
        request = MockRequest(60)
        request.impersonate_user = "anotheruser"
        request.nickname_origin = "slack"

        token = h.handle_auth(
            request,
            headers={},
            remote_addr=None,
            remote_user=None,
            authorization=("basic", DUMMY_CREDS),
        )
        self.assertEqual(token.user, "anotheruser")

    def test_standalone_impersonate_user_no_origin(self):
        h = handlers.StandaloneAuthHandler()
        request = MockRequest(60)
        request.impersonate_user = "@anotheruser"

        with self.assertRaises(exc.HTTPBadRequest):
            h.handle_auth(
                request,
                headers={},
                remote_addr=None,
                remote_user=None,
                authorization=("basic", DUMMY_CREDS),
            )

    def test_password_contains_colon(self):
        h = handlers.StandaloneAuthHandler()
        request = MockRequest(60)

        authorization = ("Basic", base64.b64encode(b"username:password:password"))
        token = h.handle_auth(
            request,
            headers={},
            remote_addr=None,
            remote_user=None,
            authorization=authorization,
        )
        self.assertEqual(token.user, "username")
