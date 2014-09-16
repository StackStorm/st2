from pecan import load_app
from oslo.config import cfg

from st2auth import config  # noqa
from st2common.models import db


cfg.CONF(args=['--config-file', '/etc/stanley/stanley.conf'])

db.db_setup(cfg.CONF.database.db_name,
            cfg.CONF.database.host,
            cfg.CONF.database.port)

pecan_config = {
    'app': {
        'root': 'st2auth.controllers.root.RootController',
        'modules': ['st2auth'],
        'debug': cfg.CONF.auth.debug,
        'errors': {'__force_dict__': True}
    }
}

application = load_app(pecan_config)
