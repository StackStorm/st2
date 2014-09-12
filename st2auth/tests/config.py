from oslo.config import cfg
from st2common import log as logging

LOG = logging.getLogger(__name__)


def _register_app_opts():
    auth_opts = [
        cfg.StrOpt('host', default='0.0.0.0'),
        cfg.IntOpt('port', default=9100),
        cfg.StrOpt('logging', default='conf/logging.conf'),
        cfg.IntOpt('token_ttl', default=86400, help='Access token ttl in seconds.'),
        cfg.BoolOpt('debug', default=False)]
    cfg.CONF.register_opts(auth_opts, group='auth')


def parse_args():
    _register_app_opts()
    cfg.CONF(args=[])
