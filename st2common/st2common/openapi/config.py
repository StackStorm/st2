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

import st2common.config as common_config
from st2common.constants.system import VERSION_STRING
from st2common.constants.system import DEFAULT_CONFIG_FILE_PATH


def parse_args(args=None):
    cfg.CONF(
        args=args,
        version=VERSION_STRING,
        default_config_files=[DEFAULT_CONFIG_FILE_PATH],
    )


def register_opts(_register_app_opts, ignore_errors=False):
    _register_common_opts(ignore_errors=ignore_errors)
    _register_app_opts(ignore_errors=ignore_errors)


def get_logging_config_path(conf_path):
    return conf_path.logging


def _register_common_opts(ignore_errors=False):
    common_config.register_opts(ignore_errors=ignore_errors)


def get_base_opts(service):
    return [
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
            default=f"/etc/st2/logging.{service}.conf",
            help="Path to the logging config.",
        ),
        cfg.BoolOpt("debug", default=False, help="Specify to enable debug mode."),
    ]
