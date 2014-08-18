import eventlet
import os
import sys

from oslo.config import cfg
from eventlet import wsgi

from st2common import log as logging
from st2common.models.db import db_setup
from st2common.models.db import db_teardown
from st2actionrunnercontroller import config
from st2actionrunnercontroller import app


eventlet.monkey_patch(
    os=True,
    select=True,
    socket=True,
    thread=False if '--use-debugger' in sys.argv else True,
    time=True)


LOG = logging.getLogger(__name__)


def __setup():
    # 1. parse args to setup config.
    config.parse_args()
    # 2. setup logging.
    logging.setup(cfg.CONF.actionrunner_controller_logging.config_file)
    # 3. all other setup which requires config to be parsed and logging to
    # be correctly setup.
    db_setup(cfg.CONF.database.db_name, cfg.CONF.database.host,
             cfg.CONF.database.port)


def __run_server():
    host = cfg.CONF.actionrunner_controller_api.host
    port = cfg.CONF.actionrunner_controller_api.port

    LOG.info("actionrunner API is serving on http://%s:%s (PID=%s)",
             host, port, os.getpid())

    wsgi.server(eventlet.listen((host, port)), app.setup_app())


def __teardown():
    db_teardown()


def main():
    try:
        __setup()
        __run_server()
    except Exception as e:
        LOG.error('Failed spinning up action runner controller: %s', e)
    finally:
        __teardown()
    return 1
