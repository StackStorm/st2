from st2reactor import config

import os
import logging
import logging.config

from oslo.config import cfg
from st2common.models.db import db_setup
from st2common.models.db import db_teardown
from st2reactor.adapter import container
from st2reactor.adapter.adapters import FixedRunAdapter, \
    DummyTriggerGeneratorAdapter

LOG = logging.getLogger('st2reactor.bin.adapter_container')


def __setup():
    # setup config before anything else.
    config.parse_args()
    # 1. setup logging.
    logging.config.fileConfig(cfg.CONF.reactor_logging.config_file,
                              defaults=None,
                              disable_existing_loggers=False)
    # 2. all other setup which requires config to be parsed and logging to
    # be correctly setup.
    db_setup(cfg.CONF.database.db_name, cfg.CONF.database.host,
             cfg.CONF.database.port)


def __teardown():
    db_teardown()


def main():
    __setup()

    LOG.info('AdapterContainer process[{}] started.'.format(os.getpid()))
    adapter_container = container.AdapterContainer(
        [FixedRunAdapter, DummyTriggerGeneratorAdapter])
    exit_code = adapter_container.main()
    LOG.info('AdapterContainer process[{}] exit with code {}.'.format(
        os.getpid(), exit_code))
    __teardown()
    return exit_code
