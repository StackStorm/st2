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
from oslo_config import cfg

try:
    import simplejson as json
except ImportError:
    import json

from st2api import app
import st2common.bootstrap.runnersregistrar as runners_registrar
from st2common.rbac.types import SystemRole
from st2common.persistence.auth import User
from st2common.persistence.rbac import UserRoleAssignment
from st2common.models.db.auth import UserDB
from st2common.models.db.rbac import UserRoleAssignmentDB
from st2common.rbac.migrations import run_all as run_all_rbac_migrations
from st2common.router import Router
from st2tests.base import DbTestCase
from st2tests.base import CleanDbTestCase
from st2tests.api import TestApp
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

        # TODO(manas) : register action types here for now. RunnerType registration can be moved
        # to posting to /runnertypes but that implies implementing POST.
        runners_registrar.register_runners()

        cls.app = TestApp(app.setup_app())


class APIControllerWithRBACTestCase(FunctionalTest, CleanDbTestCase):
    """
    Base test case class for testing API controllers with RBAC enabled.
    """

    enable_auth = True

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
            'user': user_db
        }
        self.request_context_mock = mock.PropertyMock(return_value=mock_context)
        Router.mock_context = self.request_context_mock


class FakeResponse(object):

    def __init__(self, text, status_code, reason):
        self.text = text
        self.status_code = status_code
        self.reason = reason

    def json(self):
        return json.loads(self.text)

    def raise_for_status(self):
        raise Exception(self.reason)


class BaseActionExecutionControllerTestCase(object):

    @staticmethod
    def _get_actionexecution_id(resp):
        return resp.json['id']

    @staticmethod
    def _get_liveaction_id(resp):
        return resp.json['liveaction']['id']

    def _do_get_one(self, actionexecution_id, *args, **kwargs):
        return self.app.get('/v1/executions/%s' % actionexecution_id, *args, **kwargs)

    def _do_post(self, liveaction, *args, **kwargs):
        return self.app.post_json('/v1/executions', liveaction, *args, **kwargs)

    def _do_delete(self, actionexecution_id, expect_errors=False):
        return self.app.delete('/v1/executions/%s' % actionexecution_id,
                               expect_errors=expect_errors)

    def _do_put(self, actionexecution_id, updates, *args, **kwargs):
        return self.app.put_json('/v1/executions/%s' % actionexecution_id, updates, *args, **kwargs)
