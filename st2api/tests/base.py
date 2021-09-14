# Copyright 2020 The StackStorm Authors.
# Copyright (C) 2020 Extreme Networks, Inc - All Rights Reserved
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

"""
Module containing base classes for API controller RBAC tests.
"""

from __future__ import absolute_import

from oslo_config import cfg

from st2common.rbac.types import SystemRole
from st2common.persistence.auth import User
from st2common.persistence.rbac import UserRoleAssignment
from st2common.models.db.auth import UserDB
from st2common.models.db.rbac import UserRoleAssignmentDB
from st2common.rbac.migrations import run_all as run_all_rbac_migrations
from st2tests.api import BaseFunctionalTest
from st2tests.base import CleanDbTestCase


__all__ = ["APIControllerWithRBACTestCase"]


class BaseAPIControllerWithRBACTestCase(BaseFunctionalTest, CleanDbTestCase):
    """
    Base test case class for testing API controllers with RBAC enabled.
    """

    enable_auth = True

    @classmethod
    def setUpClass(cls):
        super(BaseAPIControllerWithRBACTestCase, cls).setUpClass()

        # Make sure RBAC is enabeld
        cfg.CONF.set_override(name="enable", override=True, group="rbac")
        cfg.CONF.set_override(name="backend", override="default", group="rbac")

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
                user=user_db.name,
                role=role_name,
                source="assignments/%s.yaml" % user_db.name,
            )
            UserRoleAssignment.add_or_update(role_assignment_db)

        # Insert a user with no permissions and role assignments
        user_1_db = UserDB(name="no_permissions")
        user_1_db = User.add_or_update(user_1_db)
        self.users["no_permissions"] = user_1_db

        # Insert special system user
        user_2_db = UserDB(name="system_user")
        user_2_db = User.add_or_update(user_2_db)
        self.users["system_user"] = user_2_db

        role_assignment_db = UserRoleAssignmentDB(
            user=user_2_db.name,
            role=SystemRole.ADMIN,
            source="assignments/%s.yaml" % user_2_db.name,
        )
        UserRoleAssignment.add_or_update(role_assignment_db)


class APIControllerWithRBACTestCase(BaseAPIControllerWithRBACTestCase):
    from st2api import app

    app_module = app
