# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
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
from st2common.service_setup import db_setup
from st2common.service_setup import db_teardown
from st2common.logging.filters import LogLevelFilter
from st2common.transport.bootstrap_utils import register_exchanges

__all__ = [
    'setup',
    'teardown',

    'db_setup',
    'db_teardown'
]

LOG = logging.getLogger(__name__)


def register_common_cli_options():
    """
    Register common CLI options.
    """
    cfg.CONF.register_cli_opt(cfg.BoolOpt('verbose', short='v', default=False))


def setup(config, setup_db=True, register_mq_exchanges=True):
    """
    Common setup function.

    Currently it performs the following operations:

    1. Parses config and CLI arguments
    2. Establishes DB connection
    3. Suppress DEBUG log level if --verbose flag is not used
    4. Registers RabbitMQ exchanges

    :param config: Config object to use to parse args.
    """
    # Register common CLI options
    register_common_cli_options()

    # Parse args to setup config
    config.parse_args()

    # Set up logging
    log_level = stdlib_logging.DEBUG
    stdlib_logging.basicConfig(format='%(asctime)s %(levelname)s [-] %(message)s', level=log_level)

    if not cfg.CONF.verbose:
        # Note: We still want to print things at the following log levels: INFO, ERROR, CRITICAL
        exclude_log_levels = [stdlib_logging.AUDIT, stdlib_logging.DEBUG]
        handlers = stdlib_logging.getLoggerClass().manager.root.handlers

        for handler in handlers:
            handler.addFilter(LogLevelFilter(log_levels=exclude_log_levels))

    # All other setup code which requires config to be parsed and logging to be correctly setup
    if setup_db:
        db_setup()

    if register_mq_exchanges:
        register_exchanges()


def teardown():
    """
    Common teardown function.
    """
    db_teardown()
