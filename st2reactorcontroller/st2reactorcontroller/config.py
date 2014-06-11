"""
Configuration options registration and useful routines.
"""

from oslo.config import cfg

CONF = cfg.CONF

api_opts = [
    cfg.StrOpt('host', default='0.0.0.0', help='stackaton API server host'),
    cfg.IntOpt('port', default=9102, help='stackaton API server port')
]
CONF.register_opts(api_opts, group='reactor_controller_api')

pecan_opts = [
    cfg.StrOpt('root',
               default='st2reactorcontroller.controllers.root.RootController',
               help='Pecan root controller'),
    cfg.StrOpt('static_root', default='%(confdir)s/public'),
    cfg.StrOpt('template_path',
               default='%(confdir)s/st2reactorcontroller/templates'),
    cfg.ListOpt('modules', default=['st2reactorcontroller']),
    cfg.BoolOpt('debug', default=True),
    cfg.BoolOpt('auth_enable', default=True),
    cfg.DictOpt('errors', default={404: '/error/404', '__force_dict__': True})
]
CONF.register_opts(pecan_opts, group='reactor_pecan')

logging_opts = [
    cfg.StrOpt('config_file', default='conf/logging.conf',
               help='location of the logging.conf file')
]
CONF.register_opts(logging_opts, group='reactor_controller_logging')

db_opts = [
    cfg.StrOpt('host', default='0.0.0.0', help='host of db server'),
    cfg.IntOpt('port', default=27017, help='port of db server'),
    cfg.StrOpt('db_name', default='st2', help='name of database')
]
CONF.register_opts(db_opts, group='database')

use_debugger = cfg.BoolOpt(
    'use-debugger', default=False,
    help='Enables debugger. Note that using this option changes how the '
         'eventlet library is used to support async IO. This could result in '
         'failures that do not occur under normal operation.'
)
CONF.register_cli_opt(use_debugger)


def parse_args(args=None):
    CONF(args=args)
