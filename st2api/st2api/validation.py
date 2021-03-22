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

__all__ = ["validate_rbac_is_correctly_configured"]


def validate_rbac_is_correctly_configured():
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
