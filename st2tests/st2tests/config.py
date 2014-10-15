from oslo.config import cfg

from st2common import log as logging
import st2common.config as common_config

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


def parse_args():
    _setup_config_opts()
    CONF(args=[])


def _setup_config_opts():
    cfg.CONF.reset()
    _register_config_opts()
    _override_config_opts()


def _override_config_opts():
    _override_db_opts()


def _register_config_opts():
    _register_common_opts()
    _register_api_opts()
    _register_auth_opts()
    _register_action_sensor_opts()


def _override_db_opts():
    CONF.set_override(name='db_name', override='st2-test', group='database')


def _register_common_opts():
    try:
        common_config.register_opts(ignore_errors=True)
    except:
        LOG.exception('Common config registration failed.')


def _register_api_opts():
    api_opts = [
        cfg.StrOpt('host', default='0.0.0.0', help='action API server host'),
        cfg.IntOpt('port', default=9101, help='action API server port')
    ]
    _register_opts(api_opts, group='api')

    # XXX: note : template_path value only works if started from the top-level of the codebase.
    # Brittle!
    pecan_opts = [
        cfg.StrOpt('root',
                   default='st2api.controllers.root.RootController',
                   help='Pecan root controller'),
        cfg.StrOpt('template_path',
                   default='%(confdir)s/st2api/st2api/templates'),
        cfg.ListOpt('modules', default=['st2api']),
        cfg.BoolOpt('debug', default=True),
        cfg.BoolOpt('auth_enable', default=True),
        cfg.DictOpt('errors', default={404: '/error/404', '__force_dict__': True})
    ]
    _register_opts(pecan_opts, group='api_pecan')

    messaging_opts = [
        cfg.StrOpt('url', default='amqp://guest:guest@localhost:5672//',
                   help='URL of the messaging server.')
    ]
    _register_opts(messaging_opts, group='messaging')

    ssh_runner_opts = [
        cfg.StrOpt('remote_dir',
                   default='/tmp',
                   help='Location of the script on the remote filesystem.'),
        cfg.BoolOpt('allow_partial_failure',
                    default=False,
                    help='How partial success of actions run on multiple nodes should be treated.')
    ]
    _register_opts(ssh_runner_opts, group='ssh_runner')


def _register_auth_opts():
    auth_opts = [
        cfg.StrOpt('host', default='0.0.0.0'),
        cfg.IntOpt('port', default=9100),
        cfg.StrOpt('logging', default='conf/logging.conf'),
        cfg.IntOpt('token_ttl', default=86400, help='Access token ttl in seconds.'),
        cfg.BoolOpt('debug', default=False)
    ]
    _register_opts(auth_opts, group='auth')


def _register_action_sensor_opts():
    action_sensor_opts = [
        cfg.BoolOpt('enable', default=True,
                    help='Whether to enable or disable the ability ' +
                         'to post a trigger on action.'),
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


def _register_opts(opts, group=None):
    CONF.register_opts(opts, group)
