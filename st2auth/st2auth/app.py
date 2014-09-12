import pecan
from oslo.config import cfg

from st2common import log as logging


LOG = logging.getLogger(__name__)


def _get_pecan_config():

    config = {
        'app': {
            'root': 'st2auth.controllers.root.RootController',
            'modules': ['st2auth'],
            'debug': cfg.CONF.auth.debug,
            'errors': {'__force_dict__': True}
        }
    }

    return pecan.configuration.conf_from_dict(config)


def setup_app(config=None):

    if not config:
        config = _get_pecan_config()

    app_conf = dict(config.app)

    return pecan.make_app(
        app_conf.pop('root'),
        logging=getattr(config, 'logging', {}),
        **app_conf
    )
