import logging
from oslo.config import cfg
import pecan

from st2actioncontroller import model


LOG = logging.getLogger(__name__)


def __get_pecan_config():
    opts = cfg.CONF.action_pecan

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

    LOG.info('Creating %s as Pecan app.' % __name__)
    if not config:
        config = __get_pecan_config()

    app_conf = dict(config.app)

    model.init_model()

    app = pecan.make_app(app_conf.pop('root'),
                   logging=getattr(config, 'logging', {}),
                   **app_conf
                  ) 

    LOG.info('%s app created.' % __name__)

    return app
                   
# Original pecan make_app call below. Check on semantics of fields omitted in code above.
"""
    return make_app(
        config.app.root,
        static_root=config.app.static_root,
        template_path=config.app.template_path,
        logging=getattr(config, 'logging', {}),
        debug=getattr(config.app, 'debug', False),
        force_canonical=getattr(config.app, 'force_canonical', True),
        guess_content_type_from_ext=getattr(
            config.app,
            'guess_content_type_from_ext',
            True),
    )
"""
