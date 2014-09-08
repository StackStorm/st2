from oslo.config import cfg
from st2common import log as logging

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


def _register_opts(opts, group=None):
    try:
        CONF.register_opts(opts, group)
    except cfg.DuplicateOptError:
        LOG.exception('Will skip registration of [%s] %s.', group, opts)


def _setup_config_opts():
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
    _register_opts(action_sensor_opts, group='action_sensor')

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
    _register_opts(ssh_runner_opts, group='ssh_runner')

    api_opts = [
        cfg.StrOpt('host', default='0.0.0.0', help='ST2 API server host.'),
        cfg.IntOpt('port', default=9101, help='ST2 API server port.')
    ]
    _register_opts(api_opts, group='api')


def parse_args():
    _setup_config_opts()
    CONF(args=[])
