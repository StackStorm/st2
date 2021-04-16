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

"""
This module contains common script setup and teardown code.

Note: In this context script is every module which is not long running and can be executed from the
command line (e.g. st2-submit-debug-info, st2-register-content, etc.).
"""

from __future__ import absolute_import

import logging as stdlib_logging

from oslo_config import cfg
from st2common import log as logging
from st2common.database_setup import db_setup
from st2common.database_setup import db_teardown
from st2common import triggers
from st2common.logging.filters import LogLevelFilter
from st2common.transport.bootstrap_utils import register_exchanges_with_retry

__all__ = ["setup", "teardown", "db_setup", "db_teardown"]

LOG = logging.getLogger(__name__)


def register_common_cli_options():
    """
    Register common CLI options.
    """
    cfg.CONF.register_cli_opt(cfg.BoolOpt("verbose", short="v", default=False))


def setup(
    config,
    setup_db=True,
    register_mq_exchanges=True,
    register_internal_trigger_types=False,
    ignore_register_config_opts_errors=False,
):
    """
    Common setup function.

    Currently it performs the following operations:

    1. Parses config and CLI arguments
    2. Establishes DB connection
    3. Suppress DEBUG log level if --verbose flag is not used
    4. Registers RabbitMQ exchanges
    5. Registers internal trigger types (optional, disabled by default)

    :param config: Config object to use to parse args.
    """
    # Register common CLI options
    register_common_cli_options()

    # Parse args to setup config
    # NOTE: This code is not the best, but it's only realistic option we have at this point.
    # Refactoring all the code and config modules to avoid import time side affects would be a big
    # rabbit hole. Luckily registering same options twice is not really a big deal or fatal error
    # so we simply ignore such errors.
    if config.__name__ == "st2common.config" and ignore_register_config_opts_errors:
        config.parse_args(ignore_errors=True)
    else:
        config.parse_args()

    if cfg.CONF.debug:
        cfg.CONF.verbose = True

    # Set up logging
    log_level = stdlib_logging.DEBUG
    stdlib_logging.basicConfig(
        format="%(asctime)s %(levelname)s [-] %(message)s", level=log_level
    )

    if not cfg.CONF.verbose:
        # Note: We still want to print things at the following log levels: INFO, ERROR, CRITICAL
        exclude_log_levels = [stdlib_logging.AUDIT, stdlib_logging.DEBUG]
        handlers = stdlib_logging.getLoggerClass().manager.root.handlers

        for handler in handlers:
            handler.addFilter(LogLevelFilter(log_levels=exclude_log_levels))

        # NOTE: statsd logger logs everything by default under INFO so we ignore those log
        # messages unless verbose / debug mode is used
        logging.ignore_statsd_log_messages()

    logging.ignore_lib2to3_log_messages()

    # All other setup code which requires config to be parsed and logging to be correctly setup
    if setup_db:
        db_setup()

    if register_mq_exchanges:
        register_exchanges_with_retry()

    if register_internal_trigger_types:
        triggers.register_internal_trigger_types()


def teardown():
    """
    Common teardown function.
    """
    db_teardown()
