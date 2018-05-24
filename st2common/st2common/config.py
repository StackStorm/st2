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

from __future__ import absolute_import
import os
import platform
import socket
import sys

from oslo_config import cfg
from distutils.spawn import find_executable

from st2common.constants.system import VERSION_STRING
from st2common.constants.system import DEFAULT_CONFIG_FILE_PATH
from st2common.constants.runners import PYTHON_RUNNER_DEFAULT_LOG_LEVEL


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
        cfg.BoolOpt(
            'enable', default=False,
            help='Enable RBAC.'),
        cfg.BoolOpt(
            'sync_remote_groups', default=False,
            help='True to synchronize remote groups returned by the auth backed for each '
                 'StackStorm user with local StackStorm roles based on the group to role '
                 'mapping definition files.'),
        cfg.BoolOpt(
            'permission_isolation', default=False,
            help='Isolate resources by user. For now, these resources only include rules and '
                 'executions. All resources can only be viewed or executed by the owning user '
                 'except the admin and system_user who can view or run everything.')
    ]

    do_register_opts(rbac_opts, 'rbac', ignore_errors)

    system_user_opts = [
        cfg.StrOpt(
            'user', default='stanley',
            help='Default system user.'),
        cfg.StrOpt(
            'ssh_key_file', default='/home/stanley/.ssh/stanley_rsa',
            help='SSH private key for the system user.')
    ]

    do_register_opts(system_user_opts, 'system_user', ignore_errors)

    schema_opts = [
        cfg.IntOpt(
            'version', default=4,
            help='Version of JSON schema to use.'),
        cfg.StrOpt(
            'draft', default='http://json-schema.org/draft-04/schema#',
            help='URL to the JSON schema draft.')
    ]

    do_register_opts(schema_opts, 'schema', ignore_errors)

    system_opts = [
        cfg.BoolOpt(
            'debug', default=False,
            help='Enable debug mode.'),
        cfg.StrOpt(
            'base_path', default='/opt/stackstorm',
            help='Base path to all st2 artifacts.'),
        cfg.BoolOpt(
            'validate_trigger_parameters', default=False,
            help='True to validate parameters for non-system trigger types when creating'
                 'a rule. By default, only parameters for system triggers are validated'),
        cfg.BoolOpt(
            'validate_trigger_payload', default=False,
            help='True to validate payload for non-system trigger types when dispatching a trigger '
                 'inside the sensor. By default, only payload for system triggers is validated.')
    ]

    do_register_opts(system_opts, 'system', ignore_errors)

    system_packs_base_path = os.path.join(cfg.CONF.system.base_path, 'packs')
    system_runners_base_path = os.path.join(cfg.CONF.system.base_path, 'runners')

    content_opts = [
        cfg.StrOpt(
            'pack_group', default='st2packs',
            help='User group that can write to packs directory.'),
        cfg.StrOpt(
            'system_packs_base_path', default=system_packs_base_path,
            help='Path to the directory which contains system packs.'),
        cfg.StrOpt(
            'system_runners_base_path', default=system_runners_base_path,
            help='Path to the directory which contains system runners.'),
        cfg.StrOpt(
            'packs_base_paths', default=None,
            help='Paths which will be searched for integration packs.'),
        cfg.StrOpt(
            'runners_base_paths', default=None,
            help='Paths which will be searched for runners.'),
        cfg.ListOpt(
            'index_url', default=['https://index.stackstorm.org/v1/index.json'],
            help='A URL pointing to the pack index. StackStorm Exchange is used by '
                 'default. Use a comma-separated list for multiple indexes if you '
                 'want to get other packs discovered with "st2 pack search".'),
    ]

    do_register_opts(content_opts, 'content', ignore_errors)

    webui_opts = [
        cfg.StrOpt(
            'webui_base_url', default='https://%s' % socket.getfqdn(),
            help='Base https URL to access st2 Web UI. This is used to construct history URLs '
                 'that are sent out when chatops is used to kick off executions.')
    ]

    do_register_opts(webui_opts, 'webui', ignore_errors)

    db_opts = [
        cfg.StrOpt(
            'host', default='127.0.0.1',
            help='host of db server'),
        cfg.IntOpt(
            'port', default=27017,
            help='port of db server'),
        cfg.StrOpt(
            'db_name', default='st2',
            help='name of database'),
        cfg.StrOpt(
            'username',
            help='username for db login'),
        cfg.StrOpt(
            'password',
            help='password for db login'),
        cfg.IntOpt(
            'connection_retry_max_delay_m', default=3,
            help='Connection retry total time (minutes).'),
        cfg.IntOpt(
            'connection_retry_backoff_max_s', default=10,
            help='Connection retry backoff max (seconds).'),
        cfg.IntOpt(
            'connection_retry_backoff_mul', default=1,
            help='Backoff multiplier (seconds).'),
        cfg.BoolOpt(
            'ssl', default=False,
            help='Create the connection to mongodb using SSL'),
        cfg.StrOpt(
            'ssl_keyfile', default=None,
            help='Private keyfile used to identify the local connection against MongoDB.'),
        cfg.StrOpt(
            'ssl_certfile', default=None,
            help='Certificate file used to identify the localconnection'),
        cfg.StrOpt(
            'ssl_cert_reqs', default=None, choices='none, optional, required',
            help='Specifies whether a certificate is required from the other side of the '
                 'connection, and whether it will be validated if provided'),
        cfg.StrOpt(
            'ssl_ca_certs', default=None,
            help='ca_certs file contains a set of concatenated CA certificates, which are '
                 'used to validate certificates passed from MongoDB.'),
        cfg.BoolOpt(
            'ssl_match_hostname', default=True,
            help='If True and `ssl_cert_reqs` is not None, enables hostname verification')
    ]

    do_register_opts(db_opts, 'database', ignore_errors)

    messaging_opts = [
        # It would be nice to be able to deprecate url and completely switch to using
        # url. However, this will be a breaking change and will have impact so allowing both.
        cfg.StrOpt(
            'url', default='amqp://guest:guest@127.0.0.1:5672//',
            help='URL of the messaging server.'),
        cfg.ListOpt(
            'cluster_urls', default=[],
            help='URL of all the nodes in a messaging service cluster.'),
        cfg.IntOpt(
            'connection_retries', default=10,
            help='How many times should we retry connection before failing.'),
        cfg.IntOpt(
            'connection_retry_wait', default=10000,
            help='How long should we wait between connection retries.')
    ]

    do_register_opts(messaging_opts, 'messaging', ignore_errors)

    syslog_opts = [
        cfg.StrOpt(
            'host', default='127.0.0.1',
            help='Host for the syslog server.'),
        cfg.IntOpt(
            'port', default=514,
            help='Port for the syslog server.'),
        cfg.StrOpt(
            'facility', default='local7',
            help='Syslog facility level.'),
        cfg.StrOpt(
            'protocol', default='udp',
            help='Transport protocol to use (udp / tcp).')
    ]

    do_register_opts(syslog_opts, 'syslog', ignore_errors)

    log_opts = [
        cfg.ListOpt(
            'excludes', default='',
            help='Exclusion list of loggers to omit.'),
        cfg.BoolOpt(
            'redirect_stderr', default=False,
            help='Controls if stderr should be redirected to the logs.'),
        cfg.BoolOpt(
            'mask_secrets', default=True,
            help='True to mask secrets in the log files.'),
        cfg.ListOpt(
            'mask_secrets_blacklist', default=[],
            help='Blacklist of additional attribute names to mask in the log messages.')
    ]

    do_register_opts(log_opts, 'log', ignore_errors)

    # Common API options
    api_opts = [
        cfg.StrOpt(
            'host', default='127.0.0.1',
            help='StackStorm API server host'),
        cfg.IntOpt(
            'port', default=9101,
            help='StackStorm API server port'),
        cfg.ListOpt(
            'allow_origin', default=['http://127.0.0.1:3000'],
            help='List of origins allowed for api, auth and stream'),
        cfg.BoolOpt(
            'mask_secrets', default=True,
            help='True to mask secrets in the API responses')
    ]

    do_register_opts(api_opts, 'api', ignore_errors)

    # Key Value store options
    keyvalue_opts = [
        cfg.BoolOpt(
            'enable_encryption', default=True,
            help='Allow encryption of values in key value stored qualified as "secret".'),
        cfg.StrOpt(
            'encryption_key_path', default='',
            help='Location of the symmetric encryption key for encrypting values in kvstore. '
                 'This key should be in JSON and should\'ve been generated using '
                 'st2-generate-symmetric-crypto-key tool.')
    ]

    do_register_opts(keyvalue_opts, group='keyvalue')

    # Common auth options
    auth_opts = [
        cfg.StrOpt(
            'api_url', default=None,
            help='Base URL to the API endpoint excluding the version'),
        cfg.BoolOpt(
            'enable', default=True,
            help='Enable authentication middleware.'),
        cfg.IntOpt(
            'token_ttl', default=(24 * 60 * 60),
            help='Access token ttl in seconds.'),
        # This TTL is used for tokens which belong to StackStorm services
        cfg.IntOpt(
            'service_token_ttl', default=(24 * 60 * 60),
            help='Service token ttl in seconds.')
    ]

    do_register_opts(auth_opts, 'auth', ignore_errors)

    # Runner options
    default_python_bin_path = sys.executable
    default_python3_bin_path = find_executable('python3')
    base_dir = os.path.dirname(os.path.realpath(default_python_bin_path))
    virtualenv_dir_name = 'virtualenv-osx' if platform.system() == "Darwin" else 'virtualenv'
    default_virtualenv_bin_path = os.path.join(base_dir, virtualenv_dir_name)

    action_runner_opts = [
        # Common runner options
        cfg.StrOpt(
            'logging', default='conf/logging.conf',
            help='location of the logging.conf file'),

        # Python runner options
        cfg.StrOpt(
            'python_binary', default=default_python_bin_path,
            help='Python binary which will be used by Python actions.'),
        cfg.StrOpt(
            'python3_binary', default=default_python3_bin_path,
            help='Python 3 binary which will be used by Python actions for packs which '
                 'use Python 3 virtual environment'),
        cfg.StrOpt(
            'virtualenv_binary', default=default_virtualenv_bin_path,
            help='Virtualenv binary which should be used to create pack virtualenvs.'),
        cfg.StrOpt(
            'python_runner_log_level', default=PYTHON_RUNNER_DEFAULT_LOG_LEVEL,
            help='Default log level to use for Python runner actions. Can be overriden on '
                 'invocation basis using "log_level" runner parameter.'),
        cfg.ListOpt(
            'virtualenv_opts', default=['--system-site-packages'],
            help='List of virtualenv options to be passsed to "virtualenv" command that '
                 'creates pack virtualenv.'),
        cfg.BoolOpt(
            'stream_output', default=True,
            help='True to store and stream action output (stdout and stderr) in real-time.')
    ]

    do_register_opts(action_runner_opts, group='actionrunner')

    dispatcher_pool_opts = [
        cfg.IntOpt(
            'workflows_pool_size', default=40,
            help='Internal pool size for dispatcher used by workflow actions.'),
        cfg.IntOpt(
            'actions_pool_size', default=60,
            help='Internal pool size for dispatcher used by regular actions.')
    ]

    do_register_opts(dispatcher_pool_opts, group='actionrunner')

    ssh_runner_opts = [
        cfg.StrOpt(
            'remote_dir', default='/tmp',
            help='Location of the script on the remote filesystem.'),
        cfg.BoolOpt(
            'allow_partial_failure', default=False,
            help='How partial success of actions run on multiple nodes should be treated.'),
        cfg.IntOpt(
            'max_parallel_actions', default=50,
            help='Max number of parallel remote SSH actions that should be run. '
                 'Works only with Paramiko SSH runner.'),
        cfg.BoolOpt(
            'use_ssh_config', default=False,
            help='Use the .ssh/config file. Useful to override ports etc.'),
        cfg.StrOpt(
            'ssh_config_file_path', default='~/.ssh/config',
            help='Path to the ssh config file.')
    ]

    do_register_opts(ssh_runner_opts, group='ssh_runner')

    cloudslang_opts = [
        cfg.StrOpt(
            'home_dir', default='/opt/cslang',
            help='CloudSlang home directory.'),
    ]

    do_register_opts(cloudslang_opts, group='cloudslang')

    # Common options (used by action runner and sensor container)
    action_sensor_opts = [
        cfg.BoolOpt(
            'enable', default=True,
            help='Whether to enable or disable the ability to post a trigger on action.'),
    ]

    do_register_opts(action_sensor_opts, group='action_sensor')

    # Common options for content
    pack_lib_opts = [
        cfg.BoolOpt(
            'enable_common_libs', default=False,
            help='Enable/Disable support for pack common libs. '
                 'Setting this config to ``True`` would allow you to '
                 'place common library code for sensors and actions in lib/ folder '
                 'in packs and use them in python sensors and actions. '
                 'See https://docs.stackstorm.com/reference/'
                 'sharing_code_sensors_actions.html '
                 'for details.')
    ]

    do_register_opts(pack_lib_opts, group='packs')

    # Coordination options
    coord_opts = [
        cfg.StrOpt(
            'url', default=None,
            help='Endpoint for the coordination server.'),
        cfg.IntOpt(
            'lock_timeout', default=60,
            help='TTL for the lock if backend suports it.')
    ]

    do_register_opts(coord_opts, 'coordination', ignore_errors)

    # Mistral options
    mistral_opts = [
        cfg.StrOpt(
            'v2_base_url', default='http://127.0.0.1:8989/v2',
            help='v2 API root endpoint.'),
        cfg.IntOpt(
            'retry_exp_msec', default=1000,
            help='Multiplier for the exponential backoff.'),
        cfg.IntOpt(
            'retry_exp_max_msec', default=300000,
            help='Max time for each set of backoff.'),
        cfg.IntOpt(
            'retry_stop_max_msec', default=600000,
            help='Max time to stop retrying.'),
        cfg.StrOpt(
            'keystone_username', default=None,
            help='Username for authentication.'),
        cfg.StrOpt(
            'keystone_password', default=None,
            help='Password for authentication.'),
        cfg.StrOpt(
            'keystone_project_name', default=None,
            help='OpenStack project scope.'),
        cfg.StrOpt(
            'keystone_auth_url', default=None,
            help='Auth endpoint for Keystone.'),
        cfg.StrOpt(
            'cacert', default=None,
            help='Optional certificate to validate endpoint.'),
        cfg.BoolOpt(
            'insecure', default=False,
            help='Allow insecure communication with Mistral.'),
        cfg.BoolOpt(
            'enable_polling', default=False,
            help='Enable results tracking and disable callbacks.'),
        cfg.FloatOpt(
            'jitter_interval', default=0.1,
            help='Jitter interval to smooth out HTTP requests '
                 'to mistral tasks and executions API.'),
        cfg.StrOpt(
            'api_url', default=None,
            help='URL Mistral uses to talk back to the API.'
                 'If not provided it defaults to public API URL. '
                 'Note: This needs to be a base URL without API '
                 'version (e.g. http://127.0.0.1:9101)')
    ]

    do_register_opts(mistral_opts, group='mistral', ignore_errors=ignore_errors)

    # Results Tracker query module options
    # Note that these are currently used only by mistral query module.
    query_opts = [
        cfg.IntOpt(
            'thread_pool_size', default=10,
            help='Number of threads to use to query external workflow systems.'),
        cfg.FloatOpt(
            'query_interval', default=5,
            help='Time interval between queries to external workflow system.'),
        cfg.FloatOpt(
            'empty_q_sleep_time', default=1,
            help='Sleep delay in between queries when query queue is empty.'),
        cfg.FloatOpt(
            'no_workers_sleep_time', default=1,
            help='Sleep delay for query when there is no more worker in pool.')
    ]

    do_register_opts(query_opts, group='resultstracker', ignore_errors=ignore_errors)

    # XXX: This is required for us to support deprecated config group results_tracker
    query_opts = [
        cfg.IntOpt(
            'thread_pool_size',
            help='Number of threads to use to query external workflow systems.'),
        cfg.FloatOpt(
            'query_interval',
            help='Time interval between subsequent queries for a context '
                 'to external workflow system.')
    ]

    do_register_opts(query_opts, group='results_tracker', ignore_errors=ignore_errors)

    # Common stream options
    stream_opts = [
        cfg.IntOpt(
            'heartbeat', default=25,
            help='Send empty message every N seconds to keep connection open')
    ]

    do_register_opts(stream_opts, group='stream', ignore_errors=ignore_errors)

    # Common CLI options
    cli_opts = [
        cfg.BoolOpt(
            'debug', default=False,
            help='Enable debug mode. By default this will set all log levels to DEBUG.'),
        cfg.BoolOpt(
            'profile', default=False,
            help='Enable profile mode. In the profile mode all the MongoDB queries and '
                 'related profile data are logged.'),
        cfg.BoolOpt(
            'use-debugger', default=True,
            help='Enables debugger. Note that using this option changes how the '
                 'eventlet library is used to support async IO. This could result in '
                 'failures that do not occur under normal operation.')
    ]

    do_register_cli_opts(cli_opts, ignore_errors=ignore_errors)

    # Metrics Options stream options
    metrics_opts = [
        cfg.StrOpt(
            'driver', default='noop',
            help='Driver type for metrics collection.'),
        cfg.StrOpt(
            'host', default='127.0.0.1',
            help='Destination server to connect to if driver requires connection.'),
        cfg.IntOpt(
            'port', default=8125,
            help='Destination port to connect to if driver requires connection.'),
    ]

    do_register_opts(metrics_opts, group='metrics', ignore_errors=ignore_errors)


def parse_args(args=None):
    register_opts()
    cfg.CONF(args=args, version=VERSION_STRING, default_config_files=[DEFAULT_CONFIG_FILE_PATH])
