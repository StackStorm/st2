import eventlet
import os
import sys

from oslo.config import cfg
from eventlet import wsgi

from st2common import log as logging
from st2common.models import db
from st2auth import config
from st2auth import app


eventlet.monkey_patch(
    os=True,
    select=True,
    socket=True,
    thread=False if '--use-debugger' in sys.argv else True,
    time=True)

LOG = logging.getLogger(__name__)


def _setup():
    config.parse_args()
    logging.setup(cfg.CONF.auth.logging)
    db.db_setup(cfg.CONF.database.db_name,
                cfg.CONF.database.host,
                cfg.CONF.database.port)


def _run_server():
    host = cfg.CONF.auth.host
    port = cfg.CONF.auth.port

    LOG.info('(PID=%s) ST2 Auth is listening on http://%s:%s', os.getpid(), host, port)

    wsgi.server(eventlet.listen((host, port)), app.setup_app())
    return 0


def _teardown():
    db.db_teardown()


def main():
    try:
        _setup()
        return _run_server()
    except:
        LOG.exception('(PID=%s) ST2 Auth quit due to exception.', os.getpid())
        return 1
    finally:
        _teardown()
