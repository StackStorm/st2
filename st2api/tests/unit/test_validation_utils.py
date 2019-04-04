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

from st2api.validation import validate_rbac_is_correctly_configured
from st2tests import config as tests_config

__all__ = [
    'ValidationUtilsTestCase'
]


class ValidationUtilsTestCase(unittest2.TestCase):
    def setUp(self):
        super(ValidationUtilsTestCase, self).setUp()
        tests_config.parse_args()

    def test_validate_rbac_is_correctly_configured_succcess(self):
        result = validate_rbac_is_correctly_configured()
        self.assertTrue(result)

    def test_validate_rbac_is_correctly_configured_auth_not_enabled(self):
        cfg.CONF.set_override(group='rbac', name='enable', override=True)
        cfg.CONF.set_override(group='auth', name='enable', override=False)

        expected_msg = ('Authentication is not enabled. RBAC only works when authentication is '
                        'enabled. You can either enable authentication or disable RBAC.')
        self.assertRaisesRegexp(ValueError, expected_msg,
                                validate_rbac_is_correctly_configured)

    def test_validate_rbac_is_correctly_configured_non_enterprise_backend_set(self):
        cfg.CONF.set_override(group='rbac', name='enable', override=True)
        cfg.CONF.set_override(group='rbac', name='backend', override='invalid')
        cfg.CONF.set_override(group='auth', name='enable', override=True)

        expected_msg = ('You have enabled RBAC, but RBAC backend is not set to "enterprise".')
        self.assertRaisesRegexp(ValueError, expected_msg,
                                validate_rbac_is_correctly_configured)

    def test_validate_rbac_is_correctly_configured_enterprise_backend_not_available(self):
        cfg.CONF.set_override(group='rbac', name='enable', override=True)
        cfg.CONF.set_override(group='rbac', name='backend', override='enterprise')
        cfg.CONF.set_override(group='auth', name='enable', override=True)

        expected_msg = ('"enterprise" RBAC backend is not available. ')
        self.assertRaisesRegexp(ValueError, expected_msg,
                                validate_rbac_is_correctly_configured)
