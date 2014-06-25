import eventlet
import os
import sys

from oslo.config import cfg
from st2common import log as logging
from st2common.models.db import db_setup
from st2common.models.db import db_teardown
from st2reactorcontroller import app
from st2reactorcontroller import config
from wsgiref import simple_server


eventlet.monkey_patch(
    os=True,
    select=True,
    socket=True,
    thread=False if '--use-debugger' in sys.argv else True,
    time=True)

LOG = logging.getLogger(__name__)


def __setup():
    # 1. parse config args
    config.parse_args()
    # 2. setup logging.
    logging.setup(cfg.CONF.logging.config_file)

    # 3. all other setup which requires config to be parsed and logging to
    # be correctly setup.
    db_setup(cfg.CONF.database.db_name, cfg.CONF.database.host,
             cfg.CONF.database.port)


def __run_server():

    host = cfg.CONF.api.host
    port = cfg.CONF.api.port

    server = simple_server.make_server(host, port, app.setup_app())

    LOG.info("reactor API is serving on http://%s:%s (PID=%s)",
             host, port, os.getpid())

    server.serve_forever()


def __teardown():
    db_teardown()


def main():
    try:
        __setup()
        __run_server()
    except Exception, e:
        LOG.exception(e)
    finally:
        __teardown()
    return 1
