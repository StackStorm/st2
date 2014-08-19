from oslo.config import cfg
from st2common import log as logging

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


def __register_opts(opts, group=None):
    try:
        CONF.register_opts(opts, group)
    except cfg.DuplicateOptError:
        LOG.exception('Will skip registration of [%s] %s.', group, opts)


def __setup_config_opts():
    api_opts = [
        cfg.StrOpt('host', default='0.0.0.0', help='action API server host'),
        cfg.IntOpt('port', default=9101, help='action API server port')
    ]
    __register_opts(api_opts, group='action_controller_api')

    # note : template_path value only works if started from the top-level of the codebase. Brittle!
    pecan_opts = [
        cfg.StrOpt('root',
                   default='st2actioncontroller.controllers.root.RootController',
                   help='Pecan root controller'),
        cfg.StrOpt('template_path',
                   default='%(confdir)s/st2actioncontroller/st2actioncontroller/templates'),
        cfg.ListOpt('modules', default=['st2actioncontroller']),
        cfg.BoolOpt('debug', default=True),
        cfg.BoolOpt('auth_enable', default=True),
        cfg.DictOpt('errors', default={404: '/error/404', '__force_dict__': True})
    ]
    __register_opts(pecan_opts, group='action_controller_pecan')

    liveactions_opts = [
        cfg.StrOpt('liveactions_base_url', default='http://localhost:9501/liveactions',
               help='Base URL for live actions.')
    ]
    __register_opts(liveactions_opts, group='liveactions')


def parse_args():
    __setup_config_opts()
    CONF(args=[])
