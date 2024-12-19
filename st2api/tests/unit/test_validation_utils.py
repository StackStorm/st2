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

import pytest
import unittest
from oslo_config import cfg

from st2api.validation import validate_auth_cookie_is_correctly_configured
from st2api.validation import validate_rbac_is_correctly_configured
from st2tests import config as tests_config

__all__ = ["ValidationUtilsTestCase"]


class ValidationUtilsTestCase(unittest.TestCase):
    def setUp(self):
        super(ValidationUtilsTestCase, self).setUp()
        tests_config.parse_args()

    def test_validate_auth_cookie_is_correctly_configured_success(self):
        valid_values = [
            "strict",
            "lax",
            "none",
            "unset",
        ]

        cfg.CONF.set_override(group="api", name="auth_cookie_secure", override=True)

        for value in valid_values:
            cfg.CONF.set_override(
                group="api", name="auth_cookie_same_site", override=value
            )
            self.assertTrue(validate_auth_cookie_is_correctly_configured())

    def test_validate_auth_cookie_is_correctly_configured_error(self):
        invalid_values = ["strictx", "laxx", "nonex", "invalid"]

        for value in invalid_values:
            with pytest.raises(
                ValueError,
                match=r"Valid values are \[strict, lax, none, unset\], but found",
            ):
                cfg.CONF.set_override(
                    group="api", name="auth_cookie_same_site", override=value
                )

        # SameSite=none + Secure=false is not compatible
        cfg.CONF.set_override(
            group="api", name="auth_cookie_same_site", override="none"
        )
        cfg.CONF.set_override(group="api", name="auth_cookie_secure", override=False)

        expected_msg = (
            r"Failed to validate api.auth_cookie config options: Incompatible cookie attributes: "
            "when the samesite equals 'none', then the secure must be True"
        )
        self.assertRaisesRegex(
            ValueError, expected_msg, validate_auth_cookie_is_correctly_configured
        )

    def test_validate_rbac_is_correctly_configured_succcess(self):
        result = validate_rbac_is_correctly_configured()
        self.assertTrue(result)

    def test_validate_rbac_is_correctly_configured_auth_not_enabled(self):
        cfg.CONF.set_override(group="rbac", name="enable", override=True)
        cfg.CONF.set_override(group="auth", name="enable", override=False)

        expected_msg = (
            "Authentication is not enabled. RBAC only works when authentication is "
            "enabled. You can either enable authentication or disable RBAC."
        )
        self.assertRaisesRegex(
            ValueError, expected_msg, validate_rbac_is_correctly_configured
        )

    def test_validate_rbac_is_correctly_configured_non_default_backend_set(self):
        cfg.CONF.set_override(group="rbac", name="enable", override=True)
        cfg.CONF.set_override(group="rbac", name="backend", override="invalid")
        cfg.CONF.set_override(group="auth", name="enable", override=True)

        expected_msg = (
            'You have enabled RBAC, but RBAC backend is not set to "default".'
        )
        self.assertRaisesRegex(
            ValueError, expected_msg, validate_rbac_is_correctly_configured
        )

    def test_validate_rbac_is_correctly_configured_default_backend_available_success(
        self,
    ):
        cfg.CONF.set_override(group="rbac", name="enable", override=True)
        cfg.CONF.set_override(group="rbac", name="backend", override="default")
        cfg.CONF.set_override(group="auth", name="enable", override=True)
        result = validate_rbac_is_correctly_configured()
        self.assertTrue(result)
