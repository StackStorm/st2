from oslo.config import cfg
from st2common import config as st2cfg


def parse_args(args=None):
    cfg.CONF(args=args)


def _register_common_opts():
    st2cfg.register_opts()


def _register_app_opts():
    auth_opts = [
        cfg.StrOpt('host', default='0.0.0.0'),
        cfg.IntOpt('port', default=9100),
        cfg.StrOpt('logging', default='conf/logging.conf'),
        cfg.BoolOpt('debug', default=False)]
    cfg.CONF.register_opts(auth_opts, group='auth')


def register_opts():
    _register_common_opts()
    _register_app_opts()


register_opts()
