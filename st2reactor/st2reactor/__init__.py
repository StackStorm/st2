import os
import logging
import logging.config
from oslo.config import cfg
from st2reactor import config
from st2reactor.adapter import container
from st2reactor.adapter.adapters import FixedRunAdapter
from st2common.models.db import setup as db_setup
from st2common.models.db import teardown as db_teardown


LOG = logging.getLogger('st2reactor.bin.adapter_container')


def __setup():
    # 1. parse config.
    config.parse_args()
    # 2. setup logging.
    logging.config.fileConfig(cfg.CONF.reactor_logging.config_file,
                              defaults=None,
                              disable_existing_loggers=False)
    # 3. all other setup which requires config to be parsed and logging to
    # be correctly setup.
    db_setup()


def __teardown():
    db_teardown()


def main():
    __setup()

    LOG.info('AdapterContainer process[{}] started.'.format(os.getpid()))
    adapter_container = container.AdapterContainer([FixedRunAdapter,
                                                    FixedRunAdapter])
    exit_code = adapter_container.main()
    LOG.info('AdapterContainer process[{}] exit with code {}.'.format(
        os.getpid(), exit_code))
    __teardown()
    return exit_code