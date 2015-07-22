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

import unittest2
from oslo_config import cfg

from st2tests import config
from st2common.rbac import utils
from st2common.models.db.auth import UserDB
from st2common.models.db.rule import RuleDB


class RBACTestCase(unittest2.TestCase):
    @classmethod
    def setUpClass(cls):
        config.parse_args()

    def setUp(self):
        self.mocks = {}

        user_db = UserDB(name='test1')
        self.mocks['user_db'] = user_db

    def test_feature_flag_returns_true_on_rbac_disabled(self):
        # When feature RBAC is disabled, all the functions should return True
        cfg.CONF.set_override(name='enable', override=False, group='rbac')

        result = utils.user_is_admin(user=self.mocks['user_db'])
        self.assertTrue(result)

    def test_feature_flag_returns_true_on_rbac_disabled(self):
        cfg.CONF.set_override(name='enable', override=True, group='rbac')

        # TODO: Enable once checks are implemented
        return
        result = utils.user_is_admin(user=self.mocks['user_db'])
        self.assertFalse(result)
