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
from st2common import log as logging


LOG = logging.getLogger(__name__)


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
    return cfg.CONF.scheduler.logging


def _register_common_opts(ignore_errors=False):
    common_config.register_opts(ignore_errors=ignore_errors)


def _register_service_opts(ignore_errors=False):
    scheduler_opts = [
        cfg.StrOpt(
            "logging",
            default="/etc/st2/logging.scheduler.conf",
            help="Location of the logging configuration file.",
        ),
        cfg.FloatOpt(
            "execution_scheduling_timeout_threshold_min",
            default=1,
            help="How long GC to search back in minutes for orphaned scheduled actions",
        ),
        cfg.IntOpt(
            "pool_size",
            default=10,
            help="The size of the pool used by the scheduler for scheduling executions.",
        ),
        cfg.FloatOpt(
            "sleep_interval",
            default=0.10,
            help="How long (in seconds) to sleep between each action scheduler main loop run "
            "interval.",
        ),
        cfg.FloatOpt(
            "gc_interval",
            default=10,
            help="How often (in seconds) to look for zombie execution requests before rescheduling "
            "them.",
        ),
        cfg.IntOpt(
            "retry_max_attempt",
            default=10,
            help="The maximum number of attempts that the scheduler retries on error.",
        ),
        cfg.IntOpt(
            "retry_wait_msec",
            default=3000,
            help="The number of milliseconds to wait in between retries.",
        ),
    ]

    common_config.do_register_opts(
        scheduler_opts, group="scheduler", ignore_errors=ignore_errors
    )


register_opts(ignore_errors=True)
