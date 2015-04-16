import eventlet
import os
import sys

from oslo.config import cfg

from st2common import log as logging
from st2common.models.db import db_setup
from st2common.models.db import db_teardown
from st2common.constants.logging import DEFAULT_LOGGING_CONF_PATH
from st2common.transport.utils import register_exchanges
from st2common.signal_handlers import register_common_signal_handlers
from st2actions import config
from st2actions import resultstracker


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
    logging.setup(cfg.CONF.resultstracker.logging)
    # 3. all other setup which requires config to be parsed and logging to
    # be correctly setup.
    username = cfg.CONF.database.username if hasattr(cfg.CONF.database, 'username') else None
    password = cfg.CONF.database.password if hasattr(cfg.CONF.database, 'password') else None
    db_setup(cfg.CONF.database.db_name, cfg.CONF.database.host, cfg.CONF.database.port,
             username=username, password=password)
    register_exchanges()
    register_common_signal_handlers()


def _run_worker():
    LOG.info('(PID=%s) Results tracker started.', os.getpid())
    tracker = resultstracker.get_tracker()
    try:
        tracker.start()
    except (KeyboardInterrupt, SystemExit):
        LOG.info('(PID=%s) Results tracker stopped.', os.getpid())
        tracker.shutdown()
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
        LOG.exception('(PID=%s) Results tracker quit due to exception.', os.getpid())
        return 1
    finally:
        _teardown()
