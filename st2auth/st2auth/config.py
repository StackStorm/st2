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

from __future__ import absolute_import

from oslo_config import cfg

import st2common.config as common_config
from st2common.constants.auth import DEFAULT_MODE
from st2common.constants.auth import DEFAULT_BACKEND
from st2common.constants.auth import DEFAULT_SSO_BACKEND
from st2common.constants.auth import VALID_MODES
from st2common.openapi import config
from st2auth import backends as auth_backends


def parse_args(args=None):
    config.parse_args(args=args)


def register_opts(ignore_errors=False):
    config.register_opts(_register_app_opts, ignore_errors=ignore_errors)


def get_logging_config_path():
    return config.get_logging_config_path(cfg.CONF.auth)


def _register_app_opts(ignore_errors=False):
    available_backends = auth_backends.get_available_backends()

    auth_opts = config.get_base_opts("auth") + [
        cfg.StrOpt(
            "host",
            default="127.0.0.1",
            help="Host on which the service should listen on.",
        ),
        cfg.IntOpt(
            "port", default=9100, help="Port on which the service should listen on."
        ),
        cfg.StrOpt(
            "mode",
            default=DEFAULT_MODE,
            help="Authentication mode (%s)" % (",".join(VALID_MODES)),
        ),
        cfg.StrOpt(
            "backend",
            default=DEFAULT_BACKEND,
            help="Authentication backend to use in a standalone mode. Available "
            "backends: %s." % (", ".join(sorted(available_backends))),
        ),
        cfg.StrOpt(
            "backend_kwargs",
            default=None,
            help="JSON serialized arguments which are passed to the authentication "
            "backend in a standalone mode.",
        ),
        cfg.BoolOpt(
            "sso", default=False, help="Enable Single Sign On for GUI if true."
        ),
        cfg.StrOpt(
            "sso_backend",
            default=DEFAULT_SSO_BACKEND,
            help="Single Sign On backend to use when SSO is enabled. Available "
            "backends: noop, saml2.",
        ),
        cfg.StrOpt(
            "sso_backend_kwargs",
            default=None,
            help="JSON serialized arguments which are passed to the SSO backend.",
        ),
    ]

    common_config.do_register_cli_opts(
        auth_opts, group="auth", ignore_errors=ignore_errors
    )
