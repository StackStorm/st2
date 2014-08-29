"""
Configuration options registration and useful routines.
"""

from oslo.config import cfg

CONF = cfg.CONF

logging_opts = [
    cfg.StrOpt('config_file', default='conf/logging.conf',
               help='location of the logging.conf file')
]
CONF.register_opts(logging_opts, group='actionrunner_logging')

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
               default='/opt/stackstorm/actions',
               help='Path to root of artifact repository'),
    cfg.StrOpt('artifact_working_dir_path',
               default='/tmp/actionrunner',
               help='Path to the root of the working directory for live action execution.'),
]
CONF.register_opts(action_runner_opts, group='action_runner')

ssh_runner_opts = [
    cfg.StrOpt('user',
               default='stanley',
               help='User for running remote tasks via the FabricRunner.'),
    cfg.StrOpt('ssh_key_file',
               default='/home/vagrant/.ssh/stanley_rsa',
               help='SSH private key for running remote tasks via the FabricRunner.'),
    cfg.StrOpt('remote_dir',
               default='/tmp',
               help='Location of the script on the remote filesystem.'),
]
CONF.register_opts(ssh_runner_opts, group='ssh_runner')

action_sensor_opts = [
    cfg.BoolOpt('enable', default=True,
                help='Whether to enable or disable the ability to post a trigger on action.'),
    cfg.StrOpt('triggers_base_url', default='http://localhost:9101/triggertypes/',
               help='URL for action sensor to post TriggerType.'),
    cfg.StrOpt('webhook_sensor_base_url', default='http://localhost:6000/webhooks/st2/',
               help='URL for action sensor to post TriggerInstances.'),
    cfg.IntOpt('request_timeout', default=1,
               help='Timeout value of all httprequests made by action sensor.'),
    cfg.IntOpt('max_attempts', default=10,
               help='No. of times to retry registration.'),
    cfg.IntOpt('retry_wait', default=1,
               help='Amount of time to wait prior to retrying a request.')
]
CONF.register_opts(action_sensor_opts, group='action_sensor')


def parse_args(args=None):
    CONF(args=args)
