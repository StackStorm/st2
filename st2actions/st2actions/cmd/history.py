import eventlet
import os
import sys

from oslo.config import cfg

from st2common import log as logging
from st2common.models.db import db_setup
from st2common.models.db import db_teardown
from st2actions import config
from st2actions import history


LOG = logging.getLogger(__name__)


eventlet.monkey_patch(
    os=True,
    select=True,
    socket=True,
    thread=False if '--use-debugger' in sys.argv else True,
    time=True)


def _setup():
    # Parse args to setup config.
    config.parse_args()

    # Setup logging.
    logging.setup(cfg.CONF.history.logging)

    # All other setup which requires config to be parsed and logging to be correctly setup.
    username = cfg.CONF.database.username if hasattr(cfg.CONF.database, 'username') else None
    password = cfg.CONF.database.password if hasattr(cfg.CONF.database, 'password') else None
    db_setup(cfg.CONF.database.db_name, cfg.CONF.database.host, cfg.CONF.database.port,
             username=username, password=password)


def _teardown():
    db_teardown()


def main():
    try:
        _setup()
        LOG.info('(PID=%s) Historian started.', os.getpid())
        history.work()
    except (KeyboardInterrupt, SystemExit):
        LOG.info('(PID=%s) Historian stopped.', os.getpid())
        return 0
    except:
        LOG.exception('(PID=%s) Historian quit due to exception.', os.getpid())
        return 1
    finally:
        _teardown()
    return 0
