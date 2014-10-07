from oslo.config import cfg
from st2common import log as logging

LOG = logging.getLogger(__name__)


def _register_opts(opts, group=None):
    try:
        cfg.CONF.register_opts(opts, group)
    except cfg.DuplicateOptError:
        LOG.exception('Will skip registration of [%s] %s.', group, opts)


def _register_app_opts():
    auth_opts = [
        cfg.StrOpt('host', default='0.0.0.0'),
        cfg.IntOpt('port', default=9100),
        cfg.StrOpt('logging', default='conf/logging.conf'),
        cfg.IntOpt('token_ttl', default=86400, help='Access token ttl in seconds.'),
        cfg.BoolOpt('debug', default=False)]
    _register_opts(auth_opts, group='auth')

    system_user_opts = [
        cfg.StrOpt('user',
                   default='stanley',
                   help='Default system user.'),
        cfg.StrOpt('ssh_key_file',
                   default='/home/vagrant/.ssh/stanley_rsa',
                   help='SSH private key for the system user.')
    ]
    _register_opts(system_user_opts, 'system_user')


def parse_args():
    _register_app_opts()
    cfg.CONF(args=[])
