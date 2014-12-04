import eventlet
import os
import sys

from oslo.config import cfg

from st2common import log as logging
from st2common.models.db import db_setup
from st2common.models.db import db_teardown
from st2common.constants.logging import DEFAULT_LOGGING_CONF_PATH
from st2actions import config
from st2actions import worker


LOG = logging.getLogger(__name__)


eventlet.monkey_patch(
    os=True,
    select=True,
    socket=True,
    thread=False if '--use-debugger' in sys.argv else True,
    time=True)


def _setup():
    # Set up logger which logs everything which happens during and before config
    # parsing to sys.stdout
    logging.setup(DEFAULT_LOGGING_CONF_PATH)

    # 1. parse args to setup config.
    config.parse_args()
    # 2. setup logging.
    logging.setup(cfg.CONF.actionrunner.logging, disable_existing_loggers=True)
    # 3. all other setup which requires config to be parsed and logging to
    # be correctly setup.
    username = cfg.CONF.database.username if hasattr(cfg.CONF.database, 'username') else None
    password = cfg.CONF.database.password if hasattr(cfg.CONF.database, 'password') else None
    db_setup(cfg.CONF.database.db_name, cfg.CONF.database.host, cfg.CONF.database.port,
             username=username, password=password)


def _run_worker():
    LOG.info('(PID=%s) Worker started.', os.getpid())
    try:
        worker.work()
    except (KeyboardInterrupt, SystemExit):
        LOG.info('(PID=%s) Worker stopped.', os.getpid())
    except:
        return 1
    return 0


def _teardown():
    db_teardown()


def main():
    try:
        _setup()
        return _run_worker()
    except SystemExit as exit_code:
        sys.exit(exit_code)
    except:
        LOG.exception('(PID=%s) Worker quit due to exception.', os.getpid())
        return 1
    finally:
        _teardown()
