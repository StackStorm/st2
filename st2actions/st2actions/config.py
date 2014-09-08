"""
Configuration options registration and useful routines.
"""

from oslo.config import cfg

import st2common.config as common_config
common_config.register_opts()

CONF = cfg.CONF

logging_opts = [
    cfg.StrOpt('logging', default='conf/logging.conf',
               help='location of the logging.conf file')
]
CONF.register_opts(logging_opts, group='actionrunner')

db_opts = [
    cfg.StrOpt('host', default='0.0.0.0', help='host of db server'),
    cfg.IntOpt('port', default=27017, help='port of db server'),
    cfg.StrOpt('db_name', default='st2', help='name of database')
]
CONF.register_opts(db_opts, group='database')

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

api_opts = [
    cfg.StrOpt('host', default='0.0.0.0', help='ST2 API server host.'),
    cfg.IntOpt('port', default=9101, help='ST2 API server port.')
]
CONF.register_opts(api_opts, group='api')

workflow_opts = [
    cfg.StrOpt('url', default='http://localhost:8989/v1', help='Mistral API server endpoint.')
]
CONF.register_opts(workflow_opts, group='workflow')


def parse_args(args=None):
    CONF(args=args)
