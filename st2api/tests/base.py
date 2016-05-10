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
import pecan
from pecan.testing import load_test_app
from oslo_config import cfg


import st2common.bootstrap.runnersregistrar as runners_registrar
from st2common.rbac.types import SystemRole
from st2common.persistence.auth import User
from st2common.persistence.rbac import UserRoleAssignment
from st2common.models.db.auth import UserDB
from st2common.models.db.rbac import UserRoleAssignmentDB
from st2common.rbac.migrations import run_all as run_all_rbac_migrations
from st2tests.base import DbTestCase
from st2tests.base import CleanDbTestCase
import st2tests.config as tests_config


class FunctionalTest(DbTestCase):
    """
    Base test case class for testing API controllers with auth and RBAC disabled.
    """
    # By default auth is disabled
    enable_auth = False

    @classmethod
    def setUpClass(cls):
        super(FunctionalTest, cls).setUpClass()
        cls._do_setUpClass()

    @classmethod
    def _do_setUpClass(cls):
        tests_config.parse_args()

        cfg.CONF.set_default('enable', cls.enable_auth, group='auth')

        cfg.CONF.set_override(name='enable', override=False, group='rbac')

        opts = cfg.CONF.api_pecan
        cfg_dict = {
            'app': {
                'root': opts.root,
                'template_path': opts.template_path,
                'modules': opts.modules,
                'debug': opts.debug,
                'auth_enable': opts.auth_enable,
                'errors': {'__force_dict__': True},
                'guess_content_type_from_ext': False
            }
        }

        # TODO(manas) : register action types here for now. RunnerType registration can be moved
        # to posting to /runnertypes but that implies implementing POST.
        runners_registrar.register_runner_types()

        cls.app = load_test_app(config=cfg_dict)


class APIControllerWithRBACTestCase(FunctionalTest, CleanDbTestCase):
    """
    Base test case class for testing API controllers with RBAC enabled.
    """

    pecan_request_context_mock = None

    @classmethod
    def setUpClass(cls):
        super(APIControllerWithRBACTestCase, cls).setUpClass()

        # Make sure RBAC is enabeld
        cfg.CONF.set_override(name='enable', override=True, group='rbac')

    @classmethod
    def tearDownClass(cls):
        super(APIControllerWithRBACTestCase, cls).tearDownClass()

    def setUp(self):
        super(APIControllerWithRBACTestCase, self).setUp()

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
                user=user_db.name,
                role=role_name)
            UserRoleAssignment.add_or_update(role_assignment_db)

        # Insert a user with no permissions and role assignments
        user_1_db = UserDB(name='no_permissions')
        user_1_db = User.add_or_update(user_1_db)
        self.users['no_permissions'] = user_1_db

    def tearDown(self):
        super(APIControllerWithRBACTestCase, self).tearDown()

        # Unpatch pecan.request.context (if patched)
        if self.pecan_request_context_mock:
            self.pecan_request_context_mock.stop()
            del(type(pecan.request).context)

    def use_user(self, user_db):
        """
        Select a user which is to be used by the HTTP request following this call.
        """
        mock_context = {
            'auth': {
                'user': user_db
            }
        }
        self.pecan_request_context_mock = mock.PropertyMock(return_value=mock_context)
        type(pecan.request).context = self.pecan_request_context_mock
