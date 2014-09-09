import eventlet
import os
import sys

from oslo.config import cfg
from eventlet import wsgi

from st2common import log as logging
from st2common.models.db import db_setup
from st2common.models.db import db_teardown
from st2api import config
from st2api import app


eventlet.monkey_patch(
    os=True,
    select=True,
    socket=True,
    thread=False if '--use-debugger' in sys.argv else True,
    time=True)

LOG = logging.getLogger(__name__)


def _setup():
    # 1. parse args to setup config.
    config.parse_args()

    # 2. setup logging.
    logging.setup(cfg.CONF.api_logging.config_file)

    # 3. all other setup which requires config to be parsed and logging to
    # be correctly setup.
    db_setup(cfg.CONF.database.db_name, cfg.CONF.database.host,
             cfg.CONF.database.port)


def _run_server():

    host = cfg.CONF.api.host
    port = cfg.CONF.api.port

    LOG.info("ST2 API is serving on http://%s:%s (PID=%s)", host, port, os.getpid())

    wsgi.server(eventlet.listen((host, port)), app.setup_app())


def _teardown():
    db_teardown()


def main():
    try:
        _setup()
        _run_server()
    except Exception as e:
        LOG.warning('Exception starting up api: %s', e, exc_info=True)
    finally:
        _teardown()
    return 1
