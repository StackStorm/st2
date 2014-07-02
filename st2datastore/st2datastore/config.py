"""
Configuration options registration and useful routines.
"""

from oslo.config import cfg

CONF = cfg.CONF

api_opts = [
    cfg.StrOpt('host', default='0.0.0.0',
               help='Stanley Datastore API server host'),
    cfg.IntOpt('port', default=9103,
               help='Stanley Datastore API server port')
]

CONF.register_opts(api_opts, group='datastore_api')

pecan_opts = [
    cfg.StrOpt('root',
               default='st2datastore.controllers.root.RootController',
               help='Pecan root controller'),
    cfg.StrOpt('static_root',
               default='%(confdir)s/st2datastore/public'),
    cfg.StrOpt('template_path',
               default='%(confdir)s/st2datastore/st2datastore/templates'),
    cfg.ListOpt('modules', default=['st2datastore']),
    cfg.BoolOpt('debug', default=True),
    cfg.BoolOpt('auth_enable', default=True),
    cfg.DictOpt('errors', default={404: '/error/404', '__force_dict__': True})
]
CONF.register_opts(pecan_opts, group='datastore_pecan')

logging_opts = [
    cfg.StrOpt('config_file', default='conf/logging.conf',
               help='location of the logging.conf file')
]
CONF.register_opts(logging_opts, group='datastore_logging')

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
