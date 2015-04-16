from oslo.config import cfg

from st2common.constants.logging import DEFAULT_LOGGING_CONF_PATH
from st2common import log as logging
from st2common.models.db import db_setup
from st2common.transport.utils import register_exchanges
from st2api import app
from st2api import config


LOG = logging.getLogger(__name__)


def setup():
    # Set up logger which logs everything which happens during and before config
    # parsing to sys.stdout
    logging.setup(DEFAULT_LOGGING_CONF_PATH)

    # 1. parse args to setup config.
    config.parse_args()

    # 2. setup logging.
    logging.setup(cfg.CONF.api.logging)

    # 3. all other setup which requires config to be parsed and logging to
    # be correctly setup.
    username = cfg.CONF.database.username if hasattr(cfg.CONF.database, 'username') else None
    password = cfg.CONF.database.password if hasattr(cfg.CONF.database, 'password') else None
    db_setup(cfg.CONF.database.db_name, cfg.CONF.database.host, cfg.CONF.database.port,
             username=username, password=password)
    register_exchanges()

    # 4. setup an application.
    return app.setup_app()
