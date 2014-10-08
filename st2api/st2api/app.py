from oslo.config import cfg
import pecan
from pecan.hooks import PecanHook

from st2common import log as logging
from st2common.middleware import auth
from st2api.version import version_string


LOG = logging.getLogger(__name__)


class CorsHook(PecanHook):

    def after(self, state):
        # TODO: Figure out proper CORS rules
        state.response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
        state.response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        state.response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        if not state.response.headers['Content-Length']:
            state.response.headers['Content-Length'] = str(len(state.response.body))


def __get_pecan_config():
    opts = cfg.CONF.api_pecan

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
    LOG.info(version_string)

    LOG.info('Creating %s as Pecan app.' % __name__)
    if not config:
        config = __get_pecan_config()

    app_conf = dict(config.app)

    app = pecan.make_app(app_conf.pop('root'),
                         logging=getattr(config, 'logging', {}),
                         hooks=[CorsHook()],
                         **app_conf
                         )

    if cfg.CONF.auth.enable:
        app = auth.AuthMiddleware(app)

    LOG.info('%s app created.' % __name__)

    return app
