from oslo.config import cfg

CONF = cfg.CONF

api_opts = [
    cfg.StrOpt('host', default='0.0.0.0', help='stackaton API server host'),
    cfg.IntOpt('port', default=9104, help='stackaton API server port')
]
CONF.register_opts(api_opts, group='reactor_api')

pecan_opts = [
    cfg.StrOpt('root',
               default='st2reactor.controllers.root.RootController',
               help='Pecan root controller'),
    cfg.StrOpt('static_root', default='%(confdir)s/public'),
    cfg.StrOpt('template_path',
               default='%(confdir)s/st2reactor/templates'),
    cfg.ListOpt('modules', default=['st2reactor']),
    cfg.BoolOpt('debug', default=False),
    cfg.BoolOpt('auth_enable', default=True),
    cfg.DictOpt('errors', default={})
]
CONF.register_opts(pecan_opts, group='reactor_pecan')

logging_opts = [
    cfg.StrOpt('config_file', default='etc/logging.conf',
               help='location of the logging.conf file')
]
CONF.register_opts(logging_opts, group='reactor_logging')

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

sensors_opts = [
    cfg.StrOpt('modules_path', default='/var/lib/stanley/sensors/modules/',
        help='path to load sensor modules from'),
    cfg.StrOpt('scripts_path', default='/var/lib/stanley/sensors/scripts',
        help='path to load sensor scripts from'),
    cfg.StrOpt('system_path', default='st2reactor/st2reactor/sensor/samples',
        help='path to load system sensor modules from')
]
CONF.register_opts(sensors_opts, group='sensors')

sensor_test_opt = cfg.StrOpt('sensor-path', help='Path to the sensor to test.')
CONF.register_cli_opt(sensor_test_opt)

reactor_opts = [
    cfg.StrOpt('actionexecution_base_url', default='http://0.0.0.0:9101/actionexecutions',
               help='URL of POSTing to the actionexecution endpoint.')
]
CONF.register_opts(reactor_opts, group='reactor')


def parse_args(args=None):
    CONF(args=args)
