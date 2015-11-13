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

import os

from oslo_config import cfg

from st2common.constants.system import VERSION_STRING


def do_register_opts(opts, group=None, ignore_errors=False):
    try:
        cfg.CONF.register_opts(opts, group=group)
    except:
        if not ignore_errors:
            raise


def do_register_cli_opts(opt, ignore_errors=False):
    # TODO: This function has broken name, it should work with lists :/
    if not isinstance(opt, (list, tuple)):
        opts = [opt]
    else:
        opts = opt

    try:
        cfg.CONF.register_cli_opts(opts)
    except:
        if not ignore_errors:
            raise


def register_opts(ignore_errors=False):
    auth_opts = [
        cfg.BoolOpt('enable', default=True, help='Enable authentication middleware.'),
        cfg.IntOpt('token_ttl', default=86400, help='Access token ttl in seconds.')
    ]
    do_register_opts(auth_opts, 'auth', ignore_errors)

    rbac_opts = [
        cfg.BoolOpt('enable', default=False, help='Enable RBAC.'),
    ]
    do_register_opts(rbac_opts, 'rbac', ignore_errors)

    system_user_opts = [
        cfg.StrOpt('user',
                   default='stanley',
                   help='Default system user.'),
        cfg.StrOpt('ssh_key_file',
                   default='/home/vagrant/.ssh/stanley_rsa',
                   help='SSH private key for the system user.')
    ]
    do_register_opts(system_user_opts, 'system_user', ignore_errors)

    schema_opts = [
        cfg.IntOpt('version', default=4, help='Version of JSON schema to use.'),
        cfg.StrOpt('draft', default='http://json-schema.org/draft-04/schema#',
                   help='URL to the JSON schema draft.')
    ]
    do_register_opts(schema_opts, 'schema', ignore_errors)

    system_opts = [
        cfg.StrOpt('base_path', default='/opt/stackstorm',
                   help='Base path to all st2 artifacts.'),
        cfg.ListOpt('admin_users', default=[],
                    help='A list of usernames for users which should have admin privileges')
    ]
    do_register_opts(system_opts, 'system', ignore_errors)

    system_packs_base_path = os.path.join(cfg.CONF.system.base_path, 'packs')
    content_opts = [
        cfg.StrOpt('system_packs_base_path', default=system_packs_base_path,
                   help='Path to the directory which contains system packs.'),
        cfg.StrOpt('packs_base_paths', default=None,
                   help='Paths which will be searched for integration packs.')
    ]
    do_register_opts(content_opts, 'content', ignore_errors)

    db_opts = [
        cfg.StrOpt('host', default='0.0.0.0', help='host of db server'),
        cfg.IntOpt('port', default=27017, help='port of db server'),
        cfg.StrOpt('db_name', default='st2', help='name of database'),
        cfg.StrOpt('username', help='username for db login'),
        cfg.StrOpt('password', help='password for db login'),
        cfg.IntOpt('connection_retry_max_delay_m', help='Connection retry total time (minutes).',
                   default=3),
        cfg.IntOpt('connection_retry_backoff_max_s', help='Connection retry backoff max (seconds).',
                   default=10),
        cfg.IntOpt('connection_retry_backoff_mul', help='Backoff multiplier (seconds).',
                   default=1)
    ]
    do_register_opts(db_opts, 'database', ignore_errors)

    messaging_opts = [
        # It would be nice to be able to deprecate url and completely switch to using
        # url. However, this will be a breaking change and will have impact so allowing both.
        cfg.StrOpt('url', default='amqp://guest:guest@127.0.0.1:5672//',
                   help='URL of the messaging server.'),
        cfg.ListOpt('cluster_urls', default=[],
                    help='URL of all the nodes in a messaging service cluster.')
    ]
    do_register_opts(messaging_opts, 'messaging', ignore_errors)

    syslog_opts = [
        cfg.StrOpt('host', default='127.0.0.1',
                   help='Host for the syslog server.'),
        cfg.IntOpt('port', default=514,
                   help='Port for the syslog server.'),
        cfg.StrOpt('facility', default='local7',
                   help='Syslog facility level.'),
        cfg.StrOpt('protocol', default='udp',
                   help='Transport protocol to use (udp / tcp).')
    ]
    do_register_opts(syslog_opts, 'syslog', ignore_errors)

    log_opts = [
        cfg.ListOpt('excludes', default='',
                    help='Exclusion list of loggers to omit.'),
        cfg.BoolOpt('redirect_stderr', default=False,
                    help='Controls if stderr should be redirected to the logs.'),
        cfg.BoolOpt('mask_secrets', default=True,
                    help='True to mask secrets in the log files.')
    ]
    do_register_opts(log_opts, 'log', ignore_errors)

    # Common API options
    api_opts = [
        cfg.StrOpt('host', default='0.0.0.0', help='StackStorm API server host'),
        cfg.IntOpt('port', default=9101, help='StackStorm API server port')
    ]
    do_register_opts(api_opts, 'api', ignore_errors)

    # Common auth options
    auth_opts = [
        cfg.StrOpt('api_url', default=None,
                   help='Base URL to the API endpoint excluding the version')
    ]
    do_register_opts(auth_opts, 'auth', ignore_errors)

    # Common options (used by action runner and sensor container)
    action_sensor_opts = [
        cfg.BoolOpt('enable', default=True,
                    help='Whether to enable or disable the ability to post a trigger on action.'),
    ]
    do_register_opts(action_sensor_opts, group='action_sensor')

    # Coordination options
    coord_opts = [
        cfg.StrOpt('url', default=None, help='Endpoint for the coordination server.'),
        cfg.IntOpt('lock_timeout', default=60, help='TTL for the lock if backend suports it.')
    ]
    do_register_opts(coord_opts, 'coordination', ignore_errors)

    # Mistral options
    mistral_opts = [
        cfg.StrOpt('v2_base_url', default='http://127.0.0.1:8989/v2', help='v2 API root endpoint.'),
        cfg.IntOpt('max_attempts', default=180, help='Max attempts to reconnect.'),
        cfg.IntOpt('retry_wait', default=5, help='Seconds to wait before reconnecting.'),
        cfg.StrOpt('keystone_username', default=None, help='Username for authentication.'),
        cfg.StrOpt('keystone_password', default=None, help='Password for authentication.'),
        cfg.StrOpt('keystone_project_name', default=None, help='OpenStack project scope.'),
        cfg.StrOpt('keystone_auth_url', default=None, help='Auth endpoint for Keystone.'),

        cfg.StrOpt('api_url', default=None, help=('URL Mistral uses to talk back to the API.'
            'If not provided it defaults to public API URL. Note: This needs to be a base '
            'URL without API version (e.g. http://127.0.0.1:9101)'))
    ]
    do_register_opts(mistral_opts, group='mistral', ignore_errors=ignore_errors)

    # Common CLI options
    debug = cfg.BoolOpt('debug', default=False,
        help='Enable debug mode. By default this will set all log levels to DEBUG.')
    profile = cfg.BoolOpt('profile', default=False,
        help=('Enable profile mode. In the profile mode all the MongoDB queries and related '
              'profile data are logged.'))
    use_debugger = cfg.BoolOpt('use-debugger', default=True,
        help='Enables debugger. Note that using this option changes how the '
             'eventlet library is used to support async IO. This could result in '
             'failures that do not occur under normal operation.')

    cli_opts = [debug, profile, use_debugger]
    do_register_cli_opts(cli_opts, ignore_errors=ignore_errors)


def parse_args(args=None):
    register_opts()
    cfg.CONF(args=args, version=VERSION_STRING)
