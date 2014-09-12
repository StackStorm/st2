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
    LOG.info("Auth service is listening on http://%s:%s (PID=%s)", host, port, os.getpid())
    wsgi.server(eventlet.listen((host, port)), app.setup_app())


def _teardown():
    db.db_teardown()


def main():
    try:
        _setup()
        _run_server()
    except Exception as e:
        LOG.warning('An exception occurred while launching the auth service. %s', e, exc_info=True)
    finally:
        _teardown()
    return 1
