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
    db_opts = [
        cfg.StrOpt('host', default='0.0.0.0', help='host of db server'),
        cfg.IntOpt('port', default=27017, help='port of db server'),
        cfg.StrOpt('db_name', default='st2-test', help='name of database')
    ]
    __register_opts(db_opts, group='database')

    api_opts = [
        cfg.StrOpt('host', default='0.0.0.0',
                   help='Stanley Datastore API server host'),
        cfg.IntOpt('port', default=9103,
                   help='Stanley Datastore API server port')
    ]
    __register_opts(api_opts, group='datastore_api')

    # Note: template_path value only works if started
    # from the top-level of the codebase. Brittle!
    pecan_opts = [
        cfg.StrOpt('root',
                   default='st2datastore.controllers.root.RootController',
                   help='Pecan root controller'),
        cfg.StrOpt('template_path',
                   default='%(confdir)s/st2datastore/st2datastore/templates'),
        cfg.ListOpt('modules', default=['st2datastore']),
        cfg.BoolOpt('debug', default=True),
        cfg.BoolOpt('auth_enable', default=True),
        cfg.DictOpt('errors',
                    default={404: '/error/404', '__force_dict__': True})
    ]
    __register_opts(pecan_opts, group='datastore_pecan')


def parse_args():
    __setup_config_opts()
    CONF(args=[])
