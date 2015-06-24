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

from st2tests.base import DbTestCase
from st2tests.config import parse_args
from st2common.models.db.auth import UserDB

from st2common.constants.rbac import SystemRole
from st2common.rbac.utils import request_user_is_admin
from st2common.rbac.utils import request_user_has_role
from st2common.rbac.utils import user_is_admin
from st2common.rbac.utils import user_has_role


class RBACUtilsTestCase(DbTestCase):
    @classmethod
    def setUpClass(cls):
        super(RBACUtilsTestCase, cls).setUpClass()

        # Add two mock users - one admin and one non-admin
        cls.admin_user = UserDB(name='admin_user')
        cls.admin_user.save()

        cls.regular_user = UserDB(name='regular_user')
        cls.regular_user.save()

    def setUp(self):
        parse_args()

    def test_request_is_admin_and_request_has_role(self):
        mock_request_admin_user = mock.Mock()
        mock_request_regular_user = mock.Mock()
        mock_request_admin_user.context = {'auth': {'user': self.admin_user}}
        mock_request_regular_user.context = {'auth': {'user': self.regular_user}}

        # Auth disabled, should always return true
        cfg.CONF.set_override(name='enable', override=False, group='auth')

        # Regular user
        self.assertTrue(request_user_is_admin(request=mock_request_regular_user))
        self.assertTrue(request_user_has_role(request=mock_request_regular_user,
                                              role=SystemRole.ADMIN))

        # Admin user
        self.assertTrue(request_user_is_admin(request=mock_request_admin_user))
        self.assertTrue(request_user_has_role(request=mock_request_admin_user,
                                              role=SystemRole.ADMIN))

        # Auth enabled
        cfg.CONF.set_override(name='enable', override=True, group='auth')

        # Admin user
        self.assertTrue(request_user_is_admin(request=mock_request_admin_user))
        self.assertTrue(request_user_has_role(request=mock_request_admin_user,
                                              role=SystemRole.ADMIN))

        # Regular user
        self.assertFalse(request_user_is_admin(request=mock_request_regular_user))
        self.assertFalse(request_user_has_role(request=mock_request_regular_user,
                                               role=SystemRole.ADMIN))

    def test_is_admin(self):
        # Admin user
        self.assertTrue(user_is_admin(user=self.admin_user))

        # Regular user
        self.assertFalse(user_is_admin(user=self.regular_user))

    def test_has_role(self):
        # Admin user
        self.assertTrue(user_has_role(user=self.admin_user, role=SystemRole.ADMIN))

        # Regular user
        self.assertFalse(user_has_role(user=self.regular_user, role=SystemRole.ADMIN))
