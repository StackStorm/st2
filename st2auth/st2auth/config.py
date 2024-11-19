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

from st2common import config as st2cfg
from st2common.constants.system import VERSION_STRING
from st2common.constants.system import DEFAULT_CONFIG_FILE_PATH
from st2common.constants.auth import DEFAULT_MODE
from st2common.constants.auth import DEFAULT_BACKEND
from st2common.constants.auth import DEFAULT_SSO_BACKEND
from st2common.constants.auth import VALID_MODES
from st2auth import backends as auth_backends


def parse_args(args=None):
    st2cfg.use_st2_env_vars(cfg.CONF)
    cfg.CONF(
        args=args,
        version=VERSION_STRING,
        default_config_files=[DEFAULT_CONFIG_FILE_PATH],
    )


def register_opts(ignore_errors=False):
    _register_common_opts(ignore_errors=ignore_errors)
    _register_app_opts(ignore_errors=ignore_errors)


def get_logging_config_path():
    return cfg.CONF.auth.logging


def _register_common_opts(ignore_errors=False):
    st2cfg.register_opts(ignore_errors=ignore_errors)


def _register_app_opts(ignore_errors=False):
    available_backends = auth_backends.get_available_backends()

    auth_opts = [
        cfg.StrOpt(
            "host",
            default="127.0.0.1",
            help="Host on which the service should listen on.",
        ),
        cfg.IntOpt(
            "port", default=9100, help="Port on which the service should listen on."
        ),
        cfg.BoolOpt("use_ssl", default=False, help="Specify to enable SSL / TLS mode"),
        cfg.StrOpt(
            "cert",
            default="/etc/apache2/ssl/mycert.crt",
            help='Path to the SSL certificate file. Only used when "use_ssl" is specified.',
        ),
        cfg.StrOpt(
            "key",
            default="/etc/apache2/ssl/mycert.key",
            help='Path to the SSL private key file. Only used when "use_ssl" is specified.',
        ),
        cfg.StrOpt(
            "logging",
            default="/etc/st2/logging.auth.conf",
            help="Path to the logging config.",
        ),
        cfg.BoolOpt("debug", default=False, help="Specify to enable debug mode."),
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

    st2cfg.do_register_cli_opts(auth_opts, group="auth", ignore_errors=ignore_errors)
