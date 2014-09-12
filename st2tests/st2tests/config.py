from oslo.config import cfg

from st2common import log as logging
import st2common.config as common_config

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


def __register_opts(opts, group=None):
    try:
        CONF.register_opts(opts, group)
    except cfg.DuplicateOptError:
        LOG.exception('Will skip registration of [%s] %s.', group, opts)


def __setup_config_opts():
    try:
        db_opts = [
            cfg.StrOpt('host', default='0.0.0.0', help='host of db server'),
            cfg.IntOpt('port', default=27017, help='port of db server'),
            cfg.StrOpt('db_name', default='st2-test', help='name of database')
        ]
        CONF.register_opts(db_opts, group='database')
    except cfg.DuplicateOptError:
        LOG.exception('Will skip registration.')

    try:
        common_config.register_opts(ignore_errors=True)
    except:
        LOG.exception('Common config registration failed.')


def parse_args():
    __setup_config_opts()
    CONF(args=[])
