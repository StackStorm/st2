# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from oslo.config import cfg

from st2common import log as logging
import st2common.config as common_config
from st2tests.fixturesloader import get_fixtures_base_path

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


def parse_args():
    _setup_config_opts()
    CONF(args=[])


def _setup_config_opts():
    cfg.CONF.reset()

    try:
        _register_config_opts()
    except Exception as e:
        print(e)
        # Some scripts register the options themselves which means registering them again will
        # cause a non-fatal exception
        return
    _override_config_opts()


def _override_config_opts():
    _override_db_opts()
    _override_common_opts()


def _register_config_opts():
    _register_common_opts()
    _register_api_opts()
    _register_auth_opts()
    _register_action_sensor_opts()
    _register_mistral_opts()
    _register_scheduler_opts()
    _register_exporter_opts()


def _override_db_opts():
    CONF.set_override(name='db_name', override='st2-test', group='database')


def _override_common_opts():
    packs_base_path = get_fixtures_base_path()
    CONF.set_override(name='system_packs_base_path', override=packs_base_path, group='content')
    CONF.set_override(name='api_url', override='http://localhost', group='auth')


def _register_common_opts():
    try:
        common_config.register_opts(ignore_errors=True)
    except:
        LOG.exception('Common config registration failed.')


def _register_api_opts():
    api_opts = [
        cfg.ListOpt('allow_origin', default=['http://localhost:3000', 'http://dev'],
                    help='List of origins allowed'),
        cfg.IntOpt('heartbeat', default=25,
                   help='Send empty message every N seconds to keep connection open')
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
        cfg.BoolOpt('use_ssl', default=False),
        cfg.StrOpt('mode', default='proxy'),
        cfg.StrOpt('logging', default='conf/logging.conf'),
        cfg.IntOpt('token_ttl', default=86400, help='Access token ttl in seconds.'),
        cfg.BoolOpt('debug', default=True)
    ]
    _register_opts(auth_opts, group='auth')


def _register_action_sensor_opts():
    action_sensor_opts = [
        cfg.BoolOpt('enable', default=True,
                    help='Whether to enable or disable the ability ' +
                         'to post a trigger on action.'),
        cfg.StrOpt('triggers_base_url', default='http://localhost:9101/v1/triggertypes/',
                   help='URL for action sensor to post TriggerType.'),
        cfg.IntOpt('request_timeout', default=1,
                   help='Timeout value of all httprequests made by action sensor.'),
        cfg.IntOpt('max_attempts', default=10,
                   help='No. of times to retry registration.'),
        cfg.IntOpt('retry_wait', default=1,
                   help='Amount of time to wait prior to retrying a request.')
    ]
    _register_opts(action_sensor_opts, group='action_sensor')


def _register_mistral_opts():
    mistral_opts = [
        cfg.StrOpt('v2_base_url', default='http://localhost:8989/v2',
                   help='Mistral v2 API server root endpoint.'),
        cfg.IntOpt('max_attempts', default=2),
        cfg.IntOpt('retry_wait', default=1)
    ]
    _register_opts(mistral_opts, group='mistral')


def _register_scheduler_opts():
    scheduler_opts = [
        cfg.IntOpt('delayed_execution_recovery', default=600,
                   help='The time in seconds to wait before recovering delayed action executions.'),
        cfg.IntOpt('rescheduling_interval', default=300,
                   help='The frequency for rescheduling action executions.')
    ]
    _register_opts(scheduler_opts, group='scheduler')


def _register_exporter_opts():
    exporter_opts = [
        cfg.StrOpt('dump_dir', default='/opt/stackstorm/exports/',
                   help='Directory to dump data to.')
    ]
    _register_opts(exporter_opts, group='exporter')


def _register_opts(opts, group=None):
    CONF.register_opts(opts, group)
