"""
# Server Specific Configurations
# TODO: externalize port number to a file in st2common
server = {
    'port': '9101',
    'host': '0.0.0.0'
}

# Pecan Application Configurations
app = {
    'root': 'st2actioncontroller.controllers.root.RootController',
    'modules': ['st2actioncontroller'],
    'default_renderer' : 'json',
    'static_root': '%(confdir)s/public',
    'template_path': '%(confdir)s/st2actioncontroller/templates',
    'debug': True,
    'errors': {
        404: '/error/404',
        '__force_dict__': True
    }
}

logging = {
    'loggers': {
        'root': {'level': 'INFO', 'handlers': ['console']},
        'st2actioncontroller': {'level': 'DEBUG', 'handlers': ['console']}
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        }
    },
    'formatters': {
        'simple': {
            'format': ('%(asctime)s %(levelname)-5.5s [%(name)s]'
                       '[%(threadName)s] %(message)s')
        }
    }
}

# Custom Configurations must be in Python dictionary format::
#
# foo = {'bar':'baz'}
#
# All configurations are accessible at::
# pecan.conf
"""


"""
Configuration options registration and useful routines.
"""

from oslo.config import cfg

CONF = cfg.CONF

api_opts = [
    cfg.StrOpt('host', default='0.0.0.0', help='StackStorm Live Action API server host'),
    cfg.IntOpt('port', default=9501, help='StackStorm Live Action API server port')
]
CONF.register_opts(api_opts, group='actionrunner_controller_api')

pecan_opts = [
    cfg.StrOpt('root',
               default='st2actionrunnercontroller.controllers.root.RootController',
               help='LiveAction root controller'),
    cfg.StrOpt('static_root', default='%(confdir)s/public'),
    cfg.StrOpt('template_path',
               default='%(confdir)s/st2actioncontroller/templates'),
    cfg.ListOpt('modules', default=['st2actioncontroller']),
    cfg.BoolOpt('debug', default=True),
    cfg.BoolOpt('auth_enable', default=True),
    cfg.DictOpt('errors', default={404: '/error/404', '__force_dict__': True})
]
CONF.register_opts(pecan_opts, group='action_pecan')

logging_opts = [
    cfg.StrOpt('config_file', default='conf/logging.conf',
               help='location of the logging.conf file')
]
CONF.register_opts(logging_opts, group='actionrunner_controller_logging')

db_opts = [
    cfg.StrOpt('host', default='0.0.0.0', help='host of db server'),
    cfg.IntOpt('port', default=27017, help='port of db server'),
    cfg.StrOpt('db_name', default='st2', help='name of database')
]
CONF.register_opts(db_opts, group='database')

use_debugger = cfg.BoolOpt(
    'use-debugger', default=True,
    help='Enables debugger. Note that using this option changes how the '
         'eventlet library is used to support async IO. This could result in '
         'failures that do not occur under normal operation.'
)
CONF.register_cli_opt(use_debugger)

action_runner_opts = [
               cfg.StrOpt('artifact_repo_path',
                          default='/opt/stackstorm/repo',
                          help='Path to root of artifact repository'),
               cfg.StrOpt('artifact_working_dir',
                          default='/tmp',
                          help='Path to the root of the working directory for live action execution.'),
              ]
CONF.register_opts(action_runner_opts, group='action_runner')



def parse_args(args=None):
    CONF(args=args)
