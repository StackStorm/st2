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
    __register_opts(api_opts, group='api')

    # note : template_path value only works if started from the top-level of the codebase. Brittle!
    pecan_opts = [
        cfg.StrOpt('root',
                   default='st2api.controllers.root.RootController',
                   help='Pecan root controller'),
        cfg.StrOpt('template_path',
                   default='%(confdir)s/st2api/st2api/templates'),
        cfg.ListOpt('modules', default=['st2api']),
        cfg.BoolOpt('debug', default=True),
        cfg.BoolOpt('auth_enable', default=True),
        cfg.DictOpt('errors', default={404: '/error/404', '__force_dict__': True})
    ]
    __register_opts(pecan_opts, group='api_pecan')

    messaging_opts = [
        cfg.StrOpt('url', default='librabbitmq://guest:guest@localhost:5672//',
                   help='URL of the messaging server.')
    ]
    __register_opts(messaging_opts, group='messaging')


def parse_args():
    __setup_config_opts()
    CONF(args=[])
