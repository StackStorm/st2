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

from st2common import config as common_config
from st2common.constants import system as sys_constants
from st2common.constants.system import DEFAULT_CONFIG_FILE_PATH


def parse_args(args=None):
    common_config.use_st2_env_vars(cfg.CONF)
    cfg.CONF(
        args=args,
        version=sys_constants.VERSION_STRING,
        default_config_files=[DEFAULT_CONFIG_FILE_PATH],
    )


def register_opts(ignore_errors=False):
    _register_common_opts(ignore_errors=ignore_errors)
    _register_service_opts(ignore_errors=ignore_errors)


def get_logging_config_path():
    return cfg.CONF.workflow_engine.logging


def _register_common_opts(ignore_errors=False):
    common_config.register_opts(ignore_errors=ignore_errors)


def _register_service_opts(ignore_errors=False):
    wf_engine_opts = [
        cfg.StrOpt(
            "logging",
            default="/etc/st2/logging.workflowengine.conf",
            help="Location of the logging configuration file.",
        )
    ]

    common_config.do_register_opts(wf_engine_opts, group="workflow_engine")


register_opts(ignore_errors=True)
