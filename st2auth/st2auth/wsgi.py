from pecan import load_app
from oslo.config import cfg

from st2auth import config  # noqa
from st2common.models import db


cfg.CONF(args=['--config-file', '/etc/st2/st2.conf'])

username = cfg.CONF.database.username if hasattr(cfg.CONF.database, 'username') else None
password = cfg.CONF.database.password if hasattr(cfg.CONF.database, 'password') else None
db.db_setup(cfg.CONF.database.db_name, cfg.CONF.database.host, cfg.CONF.database.port,
            username=username, password=password)

pecan_config = {
    'app': {
        'root': 'st2auth.controllers.root.RootController',
        'modules': ['st2auth'],
        'debug': cfg.CONF.auth.debug,
        'errors': {'__force_dict__': True}
    }
}

application = load_app(pecan_config)
