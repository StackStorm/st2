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

"""
Various base classes and test utility functions for API related tests.
"""

from __future__ import absolute_import

import six
import webtest
import mock
from oslo_config import cfg

from st2common.router import Router
from st2common.rbac.types import SystemRole
from st2common.persistence.auth import User
from st2common.persistence.rbac import UserRoleAssignment
from st2common.models.db.auth import UserDB
from st2common.models.db.rbac import UserRoleAssignmentDB
from st2common.rbac.migrations import run_all as run_all_rbac_migrations
from st2common.bootstrap import runnersregistrar as runners_registrar
from st2tests.base import DbTestCase
from st2tests.base import CleanDbTestCase
from st2tests import config as tests_config

__all__ = [
    'BaseFunctionalTest',
    'BaseAPIControllerWithRBACTestCase',

    'TestApp'
]


SUPER_SECRET_PARAMETER = b'SUPER_SECRET_PARAMETER_THAT_SHOULD_NEVER_APPEAR_IN_RESPONSES_OR_LOGS'
ANOTHER_SUPER_SECRET_PARAMETER = b'ANOTHER_SUPER_SECRET_PARAMETER_TO_TEST_OVERRIDING'


class ResponseValidationError(ValueError):
    pass


class ResponseLeakError(ValueError):
    pass


class TestApp(webtest.TestApp):
    def do_request(self, req, **kwargs):
        self.cookiejar.clear()

        if req.environ['REQUEST_METHOD'] != 'OPTIONS':
            # Making sure endpoint handles OPTIONS method properly
            self.options(req.environ['PATH_INFO'])

        res = super(TestApp, self).do_request(req, **kwargs)

        if res.headers.get('Warning', None):
            raise ResponseValidationError('Endpoint produced invalid response. Make sure the '
                                          'response matches OpenAPI scheme for the endpoint.')

        if not kwargs.get('expect_errors', None):
            try:
                body = res.body
            except AssertionError as e:
                if 'Iterator read after closed' in str(e):
                    body = b''
                else:
                    raise e

            if SUPER_SECRET_PARAMETER in body or ANOTHER_SUPER_SECRET_PARAMETER in body:
                raise ResponseLeakError('Endpoint response contains secret parameter. '
                                        'Find the leak.')

        if 'Access-Control-Allow-Origin' not in res.headers:
            raise ResponseValidationError('Response missing a required CORS header')

        return res


class BaseFunctionalTest(DbTestCase):
    """
    Base test case class for testing API controllers with auth and RBAC disabled.
    """

    # App used by the tests
    app_module = None

    # By default auth is disabled
    enable_auth = False

    register_runners = True

    @classmethod
    def setUpClass(cls):
        super(BaseFunctionalTest, cls).setUpClass()
        cls._do_setUpClass()

    @classmethod
    def _do_setUpClass(cls):
        tests_config.parse_args()

        cfg.CONF.set_default('enable', cls.enable_auth, group='auth')

        cfg.CONF.set_override(name='enable', override=False, group='rbac')

        # TODO(manas) : register action types here for now. RunnerType registration can be moved
        # to posting to /runnertypes but that implies implementing POST.
        if cls.register_runners:
            runners_registrar.register_runners()

        cls.app = TestApp(cls.app_module.setup_app())


class BaseAPIControllerWithRBACTestCase(BaseFunctionalTest, CleanDbTestCase):
    """
    Base test case class for testing API controllers with RBAC enabled.
    """

    enable_auth = True

    @classmethod
    def setUpClass(cls):
        super(BaseAPIControllerWithRBACTestCase, cls).setUpClass()

        # Make sure RBAC is enabeld
        cfg.CONF.set_override(name='enable', override=True, group='rbac')

    @classmethod
    def tearDownClass(cls):
        super(BaseAPIControllerWithRBACTestCase, cls).tearDownClass()

    def setUp(self):
        super(BaseAPIControllerWithRBACTestCase, self).setUp()

        self.users = {}
        self.roles = {}

        # Run RBAC migrations
        run_all_rbac_migrations()

        # Insert mock users with default role assignments
        role_names = [SystemRole.SYSTEM_ADMIN, SystemRole.ADMIN, SystemRole.OBSERVER]
        for role_name in role_names:
            user_db = UserDB(name=role_name)
            user_db = User.add_or_update(user_db)
            self.users[role_name] = user_db

            role_assignment_db = UserRoleAssignmentDB(
                user=user_db.name, role=role_name,
                source='assignments/%s.yaml' % user_db.name)
            UserRoleAssignment.add_or_update(role_assignment_db)

        # Insert a user with no permissions and role assignments
        user_1_db = UserDB(name='no_permissions')
        user_1_db = User.add_or_update(user_1_db)
        self.users['no_permissions'] = user_1_db

    def tearDown(self):
        super(BaseAPIControllerWithRBACTestCase, self).tearDown()

        if getattr(self, 'request_context_mock', None):
            self.request_context_mock.stop()
            del(Router.mock_context)

    def use_user(self, user_db):
        """
        Select a user which is to be used by the HTTP request following this call.
        """
        if not user_db:
            raise ValueError('"user_db" is mandatory')

        mock_context = {
            'user': user_db,
            'auth_info': {
                'method': 'authentication token',
                'location': 'header'
            }
        }
        self.request_context_mock = mock.PropertyMock(return_value=mock_context)
        Router.mock_context = self.request_context_mock
