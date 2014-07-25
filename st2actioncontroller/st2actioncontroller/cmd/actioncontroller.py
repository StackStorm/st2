import eventlet
import os
import sys
import glob
import json

from oslo.config import cfg
from wsgiref import simple_server

from st2common import log as logging
from st2common.models.db import db_setup
from st2common.models.db import db_teardown
from st2actioncontroller import config
from st2actioncontroller import app
from st2common.persistence.action import Action
from st2common.models.db.action import ActionDB


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
        os.makedirs(cfg.CONF.actions.modules_path)

    # 5. register actions at the modules path
    actions = glob.glob(cfg.CONF.actions.modules_path + '/*.json')    
    for action in actions:
        with open(action, 'r') as fd:
            content = json.load(fd)
            try:
                model = Action.get_by_name(str(content['name']))
            except:
                model = ActionDB()
            model.name = str(content['name'])
            model.description = str(content['description'])
            model.enabled = bool(content['enabled'])
            model.artifact_paths = [str(v) for v in content['artifact_paths']]
            model.entry_point = str(content['entry_point'])
            model.runner_type = str(content['runner_type'])
            model.parameters = dict(content['parameters'])
            model = Action.add_or_update(model)

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
    except Exception, e:
        LOG.exception(e)
    finally:
        __teardown()
    return 1
