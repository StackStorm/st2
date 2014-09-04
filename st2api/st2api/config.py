"""
Configuration options registration and useful routines.
"""

from oslo.config import cfg

CONF = cfg.CONF

api_opts = [
    cfg.StrOpt('host', default='0.0.0.0', help='StackStorm Robotinator API server host'),
    cfg.IntOpt('port', default=9101, help='StackStorm Robotinator API server port')
]
CONF.register_opts(api_opts, group='api')

pecan_opts = [
    cfg.StrOpt('root',
               default='st2api.controllers.root.RootController',
               help='Action root controller'),
    cfg.StrOpt('static_root', default='%(confdir)s/public'),
    cfg.StrOpt('template_path',
               default='%(confdir)s/st2api/templates'),
    cfg.ListOpt('modules', default=['st2api']),
    cfg.BoolOpt('debug', default=True),
    cfg.BoolOpt('auth_enable', default=True),
    cfg.DictOpt('errors', default={'__force_dict__': True})
]
CONF.register_opts(pecan_opts, group='api_pecan')

logging_opts = [
    cfg.StrOpt('config_file', default='conf/logging.conf',
               help='location of the logging.conf file')
]
CONF.register_opts(logging_opts, group='api_logging')

db_opts = [
    cfg.StrOpt('host', default='0.0.0.0', help='host of db server'),
    cfg.IntOpt('port', default=27017, help='port of db server'),
    cfg.StrOpt('db_name', default='st2', help='name of database')
]
CONF.register_opts(db_opts, group='database')

messaging_opts = [
    cfg.StrOpt('url', default='librabbitmq://guest:guest@localhost:5672//',
               help='URL of the messaging server.')
]
CONF.register_opts(messaging_opts, group='messaging')

use_debugger = cfg.BoolOpt(
    'use-debugger', default=True,
    help='Enables debugger. Note that using this option changes how the '
         'eventlet library is used to support async IO. This could result in '
         'failures that do not occur under normal operation.'
)
CONF.register_cli_opt(use_debugger)

actions_opts = [
    cfg.StrOpt('modules_path', default='/opt/stackstorm/actions',
               help='path where action plugins are located')
]
CONF.register_opts(actions_opts, group='actions')

rules_opts = [
    cfg.StrOpt('rules_path', default='/opt/stackstorm/rules',
        help='path to load rule files')
]
CONF.register_opts(rules_opts, group='rules')


def parse_args(args=None):
    CONF(args=args)
