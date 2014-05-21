import logging
import pecan
from oslo.config import cfg

LOG = logging.getLogger(__name__)


def __get_pecan_config():
    opts = cfg.CONF.reactor_pecan

    cfg_dict = {
        'app': {
            'root': opts.root,
            'static_root': opts.static_root,
            'template_path': opts.template_path,
            'modules': opts.modules,
            'debug': opts.debug,
            'auth_enable': opts.auth_enable,
            'errors': opts.errors
        }
    }

    return pecan.configuration.conf_from_dict(cfg_dict)


def setup_app(config=None):
    LOG.info('Creating Pecan app.')
    if not config:
        config = __get_pecan_config()

    app_conf = dict(config.app)

    app = pecan.make_app(
        app_conf.pop('root'),
        logging=getattr(config, 'logging', {}),
        **app_conf
    )
    LOG.info('Pecan app created.')

    return app
