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

import unittest
from oslo_config import cfg

from st2auth.validation import validate_auth_backend_is_correctly_configured
from st2tests import config as tests_config

__all__ = ["ValidationUtilsTestCase"]


class ValidationUtilsTestCase(unittest.TestCase):
    def setUp(self):
        super(ValidationUtilsTestCase, self).setUp()
        tests_config.parse_args()

    def test_validate_auth_backend_is_correctly_configured_success(self):
        result = validate_auth_backend_is_correctly_configured()
        self.assertTrue(result)

    def test_validate_auth_backend_is_correctly_configured_invalid_backend(self):
        cfg.CONF.set_override(group="auth", name="mode", override="invalid")
        expected_msg = (
            'Invalid auth mode "invalid" specified in the config. '
            "Valid modes are: proxy, standalone"
        )
        self.assertRaisesRegex(
            ValueError, expected_msg, validate_auth_backend_is_correctly_configured
        )

    def test_validate_auth_backend_is_correctly_configured_backend_doesnt_expose_groups(
        self,
    ):
        # Flat file backend doesn't expose user group membership information aha provide
        # "has group info" capability
        cfg.CONF.set_override(group="auth", name="backend", override="flat_file")
        cfg.CONF.set_override(
            group="auth", name="backend_kwargs", override='{"file_path": "dummy"}'
        )
        cfg.CONF.set_override(group="rbac", name="enable", override=True)
        cfg.CONF.set_override(group="rbac", name="sync_remote_groups", override=True)

        expected_msg = (
            "Configured auth backend doesn't expose user group information. Disable "
            "remote group synchronization or"
        )
        self.assertRaisesRegex(
            ValueError, expected_msg, validate_auth_backend_is_correctly_configured
        )
