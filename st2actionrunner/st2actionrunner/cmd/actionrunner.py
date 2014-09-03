import eventlet
import os
import sys

from oslo.config import cfg

from st2common import log as logging
from st2common.models.db import db_setup
from st2common.models.db import db_teardown
from st2actionrunner import config
from st2actionrunner import worker


eventlet.monkey_patch(
    os=True,
    select=True,
    socket=True,
    thread=False if '--use-debugger' in sys.argv else True,
    time=True)


def __setup():
    # 1. parse args to setup config.
    config.parse_args()
    # 2. setup logging.
    logging.setup(cfg.CONF.actionrunner_logging.config_file)
    # 3. all other setup which requires config to be parsed and logging to
    # be correctly setup.
    db_setup(cfg.CONF.database.db_name, cfg.CONF.database.host,
             cfg.CONF.database.port)


def __run_worker():
    LOG = logging.getLogger(__name__)
    LOG.info('[PID=%s] Worker started.', os.getpid())
    worker.work()


def __teardown():
    db_teardown()


def main():
    try:
        __setup()
        __run_worker()
    except:
        LOG = logging.getLogger(__name__)
        LOG.exception('[PID=%s] Worker quit.', os.getpid())
    finally:
        __teardown()
    return 1
