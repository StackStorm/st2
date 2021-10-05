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

from st2common.constants.auth import VALID_MODES
from st2auth.backends import get_backend_instance as get_auth_backend_instance
from st2auth.backends.constants import AuthBackendCapability

__all__ = ["validate_auth_backend_is_correctly_configured"]


def validate_auth_backend_is_correctly_configured():
    # 1. Verify correct mode is specified
    if cfg.CONF.auth.mode not in VALID_MODES:
        msg = 'Invalid auth mode "%s" specified in the config. Valid modes are: %s' % (
            cfg.CONF.auth.mode,
            ", ".join(VALID_MODES),
        )
        raise ValueError(msg)

    # 2. Verify that auth backend used by the user exposes group information
    if cfg.CONF.rbac.enable and cfg.CONF.rbac.sync_remote_groups:
        auth_backend = get_auth_backend_instance(name=cfg.CONF.auth.backend)
        capabilies = getattr(auth_backend, "CAPABILITIES", ())
        if AuthBackendCapability.HAS_GROUP_INFORMATION not in capabilies:
            msg = (
                "Configured auth backend doesn't expose user group information. Disable "
                "remote group synchronization or use a different backend which exposes "
                "user group membership information."
            )
            raise ValueError(msg)

    return True
