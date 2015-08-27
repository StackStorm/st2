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
This module contains common service setup and teardown code.
"""

from __future__ import absolute_import

import os
import logging as stdlib_logging

from oslo_config import cfg

from st2common import log as logging
from st2common.models import db
from st2common.constants.logging import DEFAULT_LOGGING_CONF_PATH
from st2common.logging.misc import set_log_level_for_all_loggers
from st2common.transport.bootstrap_utils import register_exchanges
from st2common.signal_handlers import register_common_signal_handlers

from st2common.rbac.migrations import insert_system_roles

__all__ = [
    'setup',
    'teardown',

    'db_setup',
    'db_teardown'
]

LOG = logging.getLogger(__name__)


def setup(service, config, setup_db=True, register_mq_exchanges=True,
          register_signal_handlers=True, run_migrations=True):
    """
    Common setup function.

    Currently it performs the following operations:

    1. Parses config and CLI arguments
    2. Establishes DB connection
    3. Set log level for all the loggers to DEBUG if --debug flag is present
    4. Registers RabbitMQ exchanges
    5. Registers common signal handlers

    :param service: Name of the service.
    :param config: Config object to use to parse args.
    """
    # Set up logger which logs everything which happens during and before config
    # parsing to sys.stdout
    logging.setup(DEFAULT_LOGGING_CONF_PATH)

    # Parse args to setup config.
    config.parse_args()

    config_file_paths = cfg.CONF.config_file
    config_file_paths = [os.path.abspath(path) for path in config_file_paths]
    LOG.debug('Using config files: %s', ','.join(config_file_paths))

    # Setup logging.
    logging_config_path = config.get_logging_config_path()
    logging_config_path = os.path.abspath(logging_config_path)

    LOG.debug('Using logging config: %s', logging_config_path)
    logging.setup(logging_config_path)

    if cfg.CONF.debug:
        set_log_level_for_all_loggers(level=stdlib_logging.DEBUG)

    # All other setup which requires config to be parsed and logging to
    # be correctly setup.
    if setup_db:
        db_setup()

    if register_mq_exchanges:
        register_exchanges()

    if register_signal_handlers:
        register_common_signal_handlers()

    # TODO: This is a "not so nice" workaround until we have a proper migration system in place
    if run_migrations:
        insert_system_roles()


def teardown():
    """
    Common teardown function.
    """
    db_teardown()


def db_setup():
    username = getattr(cfg.CONF.database, 'username', None)
    password = getattr(cfg.CONF.database, 'password', None)

    connection = db.db_setup(db_name=cfg.CONF.database.db_name, db_host=cfg.CONF.database.host,
                             db_port=cfg.CONF.database.port, username=username, password=password)
    return connection


def db_teardown():
    return db.db_teardown()
