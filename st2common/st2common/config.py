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
import socket
import sys

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
        cfg.BoolOpt('debug', help='Enable debug mode.', default=False),
        cfg.StrOpt('base_path', default='/opt/stackstorm',
                   help='Base path to all st2 artifacts.')
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

    webui_opts = [
        cfg.StrOpt('webui_base_url', default='https://%s' % socket.getfqdn(),
                   help='Base https URL to access st2 Web UI. This is used to construct' +
                        'history URLs that are sent out when chatops is used to kick off ' +
                        'executions.')
    ]
    do_register_opts(webui_opts, 'webui', ignore_errors)

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
                   default=1),
        cfg.BoolOpt('ssl', help='Create the connection to mongodb using SSL', default=False),
        cfg.StrOpt('ssl_keyfile',
                   help='Private keyfile used to identify the local connection against MongoDB.',
                   default=None),
        cfg.StrOpt('ssl_certfile', help='Certificate file used to identify the localconnection',
                   default=None),
        cfg.StrOpt('ssl_cert_reqs', choices='none, optional, required',
                   help='Specifies whether a certificate is required from the other side of the ' +
                        'connection, and whether it will be validated if provided',
                   default=None),
        cfg.StrOpt('ssl_ca_certs',
                   help='ca_certs file contains a set of concatenated CA certificates, which are' +
                        ' used to validate certificates passed from MongoDB.',
                   default=None),
        cfg.BoolOpt('ssl_match_hostname',
                    help='If True and `ssl_cert_reqs` is not None, enables hostname verification',
                    default=True)
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
        cfg.IntOpt('port', default=9101, help='StackStorm API server port'),
        cfg.ListOpt('allow_origin', default=['http://127.0.0.1:3000'],
                    help='List of origins allowed for api, auth and stream'),
        cfg.BoolOpt('mask_secrets', default=True,
                    help='True to mask secrets in the API responses')
    ]
    do_register_opts(api_opts, 'api', ignore_errors)

    # Key Value store options
    keyvalue_opts = [
        cfg.BoolOpt('enable_encryption', default=True,
                    help='Allow encryption of values in key value stored qualified as "secret".'),
        cfg.StrOpt('encryption_key_path', default='',
                   help='Location of the symmetric encryption key for encrypting values in ' +
                        'kvstore. This key should be in JSON and should\'ve been ' +
                        'generated using keyczar.')
    ]
    do_register_opts(keyvalue_opts, group='keyvalue')

    # Common auth options
    auth_opts = [
        cfg.StrOpt('api_url', default=None,
                   help='Base URL to the API endpoint excluding the version'),
        cfg.BoolOpt('enable', default=True, help='Enable authentication middleware.'),
        cfg.IntOpt('token_ttl', default=86400, help='Access token ttl in seconds.')
    ]
    do_register_opts(auth_opts, 'auth', ignore_errors)

    # Common action runner options
    default_python_bin_path = sys.executable
    base_dir = os.path.dirname(os.path.realpath(default_python_bin_path))
    default_virtualenv_bin_path = os.path.join(base_dir, 'virtualenv')
    action_runner_opts = [
        cfg.StrOpt('logging', default='conf/logging.conf',
                   help='location of the logging.conf file'),
        cfg.StrOpt('python_binary', default=default_python_bin_path,
                   help='Python binary which will be used by Python actions.'),
        cfg.StrOpt('virtualenv_binary', default=default_virtualenv_bin_path,
                   help='Virtualenv binary which should be used to create pack virtualenvs.'),
        cfg.ListOpt('virtualenv_opts', default=['--system-site-packages'],
                    help='List of virtualenv options to be passsed to "virtualenv" command that ' +
                         'creates pack virtualenv.')
    ]
    do_register_opts(action_runner_opts, group='actionrunner')

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
        cfg.IntOpt('retry_exp_msec', default=1000, help='Multiplier for the exponential backoff.'),
        cfg.IntOpt('retry_exp_max_msec', default=300000, help='Max time for each set of backoff.'),
        cfg.IntOpt('retry_stop_max_msec', default=600000, help='Max time to stop retrying.'),
        cfg.StrOpt('keystone_username', default=None, help='Username for authentication.'),
        cfg.StrOpt('keystone_password', default=None, help='Password for authentication.'),
        cfg.StrOpt('keystone_project_name', default=None, help='OpenStack project scope.'),
        cfg.StrOpt('keystone_auth_url', default=None, help='Auth endpoint for Keystone.'),
        cfg.StrOpt('cacert', default=None, help='Optional certificate to validate endpoint.'),
        cfg.BoolOpt('insecure', default=False, help='Allow insecure communication with Mistral.'),

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
