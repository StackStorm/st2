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

from oslo_config import cfg

from webob import cookies

__all__ = [
    "validate_auth_cookie_is_correctly_configured",
    "validate_rbac_is_correctly_configured",
]


def validate_auth_cookie_is_correctly_configured() -> bool:
    """
    Function which verifies that SameCookie config option value is correctly configured.

    This method should be called in the api init phase so we catch any misconfiguration issues
    before startup.
    """
    if cfg.CONF.api.auth_cookie_same_site not in ["strict", "lax", "none", "unset"]:
        raise ValueError(
            'Got invalid value "%s" (type %s) for cfg.CONF.api.auth_cookie_same_site config '
            "option. Valid values are: strict, lax, none, unset."
            % (
                cfg.CONF.api.auth_cookie_same_site,
                type(cfg.CONF.api.auth_cookie_same_site),
            )
        )

    # Now we try to make a dummy cookie to verify all the options are configured correctly. Some
    # Options are mutually exclusive - e.g. SameSite none and Secure false.
    try:
        # NOTE: none and unset don't mean the same thing - unset implies not setting this attribute
        # (backward compatibility) and none implies setting this attribute value to none
        same_site = cfg.CONF.api.auth_cookie_same_site

        kwargs = {}
        if same_site != "unset":
            kwargs["samesite"] = same_site

        cookies.make_cookie(
            "test_cookie",
            "dummyvalue",
            httponly=True,
            secure=cfg.CONF.api.auth_cookie_secure,
            **kwargs,
        )
    except Exception as e:
        raise ValueError(
            "Failed to validate api.auth_cookie config options: %s" % (str(e))
        )

    return True


def validate_rbac_is_correctly_configured() -> bool:
    """
    Function which verifies that RBAC is correctly set up and configured.
    """
    if not cfg.CONF.rbac.enable:
        return True

    from st2common.rbac.backends import get_available_backends

    available_rbac_backends = get_available_backends()

    # 1. Verify auth is enabled
    if not cfg.CONF.auth.enable:
        msg = (
            "Authentication is not enabled. RBAC only works when authentication is enabled. "
            "You can either enable authentication or disable RBAC."
        )
        raise ValueError(msg)

    # 2. Verify default backend is set
    if cfg.CONF.rbac.backend != "default":
        msg = (
            'You have enabled RBAC, but RBAC backend is not set to "default". '
            "For RBAC to work, you need to set "
            '"rbac.backend" config option to "default" and restart st2api service.'
        )
        raise ValueError(msg)

    # 3. Verify default RBAC backend is available
    if "default" not in available_rbac_backends:
        msg = '"default" RBAC backend is not available.'
        raise ValueError(msg)

    return True
