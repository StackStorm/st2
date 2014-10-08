from oslo.config import cfg
from st2common import log as logging

LOG = logging.getLogger(__name__)


def _do_register_opts(opts, group=None):
    try:
        cfg.CONF.register_opts(opts, group)
    except cfg.DuplicateOptError:
        LOG.exception('Will skip registration of [%s] %s.', group, opts)


def _register_opts():
    auth_opts = [
        cfg.BoolOpt('enable', default=True, help='Enable authentication middleware.'),
        cfg.IntOpt('token_ttl', default=86400, help='Access token ttl in seconds.')
    ]
    _do_register_opts(auth_opts, 'auth')

    system_user_opts = [
        cfg.StrOpt('user',
                   default='stanley',
                   help='Default system user.'),
        cfg.StrOpt('ssh_key_file',
                   default='/home/vagrant/.ssh/stanley_rsa',
                   help='SSH private key for the system user.')
    ]
    _do_register_opts(system_user_opts, 'system_user')


def parse_args():
    _register_opts()
    cfg.CONF(args=[])
