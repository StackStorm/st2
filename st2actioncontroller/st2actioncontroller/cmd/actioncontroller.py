import eventlet
import os
import sys

from oslo.config import cfg
from wsgiref import simple_server

from st2common import log as logging
from st2common.models.db import db_setup
from st2common.models.db import db_teardown
from st2actioncontroller import config
from st2actioncontroller import app
from st2actioncontroller import model


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
    logging.setup(cfg.CONF.action_controller_logging.config_file)

    # 3. all other setup which requires config to be parsed and logging to
    # be correctly setup.
    db_setup(cfg.CONF.database.db_name, cfg.CONF.database.host,
             cfg.CONF.database.port)

    # 4. ensure paths exist
    if not os.path.exists(cfg.CONF.actions.modules_path):
        try:
            os.makedirs(cfg.CONF.actions.modules_path)
        except Exception as e:
            LOG.warning('Failed to create directory: %s, %s', cfg.CONF.actions.modules_path, e,
                        exc_info=True)

    # 5. register runnertypes and actions. The order is important because actions require action
    #    types to be present in the system.
    try:
        model.register_runner_types()
    except Exception as e:
        LOG.warning('Failed to register action types: %s', e, exc_info=True)
        LOG.warning('Not registering stock actions.')
    else:
        try:
            model.register_actions()
        except Exception as e:
            LOG.warning('Failed to register actions: %s', e, exc_info=True)


def __run_server():

    host = cfg.CONF.action_controller_api.host
    port = cfg.CONF.action_controller_api.port

    server = simple_server.make_server(host, port, app.setup_app())

    LOG.info("action API is serving on http://%s:%s (PID=%s)",
             host, port, os.getpid())

    server.serve_forever()


def __teardown():
    db_teardown()


def main():
    try:
        __setup()
        __run_server()
    except Exception as e:
        LOG.warning('Exception starting up action controller: %s', e, exc_info=True)
    finally:
        __teardown()
    return 1
