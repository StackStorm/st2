# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
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
import socket
import sys

from oslo_config import cfg
from oslo_config.sources._environment import EnvironmentConfigurationSource

from st2common.constants.system import VERSION_STRING
from st2common.constants.system import DEFAULT_CONFIG_FILE_PATH
from st2common.constants.runners import PYTHON_RUNNER_DEFAULT_LOG_LEVEL
from st2common.constants.action import LIVEACTION_COMPLETED_STATES

__all__ = ["do_register_opts", "do_register_cli_opts", "parse_args"]


def do_register_opts(opts, group=None, ignore_errors=False):
    try:
        cfg.CONF.register_opts(opts, group=group)
    except:
        if not ignore_errors:
            raise


def do_register_cli_opts(opt, ignore_errors=False, group=None):
    # TODO: This function has broken name, it should work with lists :/
    if not isinstance(opt, (list, tuple)):
        opts = [opt]
    else:
        opts = opt

    kwargs = {}
    if group:
        kwargs["group"] = group

    try:
        cfg.CONF.register_cli_opts(opts, **kwargs)
    except:
        if not ignore_errors:
            raise


def register_opts(ignore_errors=False):
    rbac_opts = [
        cfg.BoolOpt("enable", default=False, help="Enable RBAC."),
        cfg.StrOpt("backend", default="noop", help="RBAC backend to use."),
        cfg.BoolOpt(
            "sync_remote_groups",
            default=False,
            help="True to synchronize remote groups returned by the auth backed for each "
            "StackStorm user with local StackStorm roles based on the group to role "
            "mapping definition files.",
        ),
        cfg.BoolOpt(
            "permission_isolation",
            default=False,
            help="Isolate resources by user. For now, these resources only include rules and "
            "executions. All resources can only be viewed or executed by the owning user "
            "except the admin and system_user who can view or run everything.",
        ),
    ]

    do_register_opts(rbac_opts, "rbac", ignore_errors)

    system_user_opts = [
        cfg.StrOpt("user", default="stanley", help="Default system user."),
        cfg.StrOpt(
            "ssh_key_file",
            default="/home/stanley/.ssh/stanley_rsa",
            help="SSH private key for the system user.",
        ),
    ]

    do_register_opts(system_user_opts, "system_user", ignore_errors)

    schema_opts = [
        cfg.IntOpt("version", default=4, help="Version of JSON schema to use."),
        cfg.StrOpt(
            "draft",
            default="http://json-schema.org/draft-04/schema#",
            help="URL to the JSON schema draft.",
        ),
    ]

    do_register_opts(schema_opts, "schema", ignore_errors)

    system_opts = [
        cfg.BoolOpt("debug", default=False, help="Enable debug mode."),
        cfg.StrOpt(
            "base_path",
            default="/opt/stackstorm",
            help="Base path to all st2 artifacts.",
        ),
        cfg.BoolOpt(
            "validate_trigger_parameters",
            default=True,
            help="True to validate parameters for non-system trigger types when creating"
            "a rule. By default, only parameters for system triggers are validated.",
        ),
        cfg.BoolOpt(
            "validate_trigger_payload",
            default=True,
            help="True to validate payload for non-system trigger types when dispatching a trigger "
            "inside the sensor. By default, only payload for system triggers is validated.",
        ),
        cfg.BoolOpt(
            "validate_output_schema",
            default=False,
            help="True to validate action and runner output against schema.",
        ),
    ]

    do_register_opts(system_opts, "system", ignore_errors)

    system_packs_base_path = os.path.join(cfg.CONF.system.base_path, "packs")
    system_runners_base_path = os.path.join(cfg.CONF.system.base_path, "runners")

    content_opts = [
        cfg.StrOpt(
            "pack_group",
            default="st2packs",
            help="User group that can write to packs directory.",
        ),
        cfg.StrOpt(
            "system_packs_base_path",
            default=system_packs_base_path,
            help="Path to the directory which contains system packs.",
        ),
        cfg.StrOpt(
            "system_runners_base_path",
            default=system_runners_base_path,
            help="Path to the directory which contains system runners.",
            deprecated_for_removal=True,
            deprecated_reason="Option unused since StackStorm v3.0.0",
            deprecated_since="3.0.0",
        ),
        cfg.StrOpt(
            "packs_base_paths",
            default=None,
            help="Paths which will be searched for integration packs.",
        ),
        cfg.StrOpt(
            "runners_base_paths",
            default=None,
            help="Paths which will be searched for runners.",
            deprecated_for_removal=True,
            deprecated_reason="Option unused since StackStorm v3.0.0",
            deprecated_since="3.0.0",
        ),
        cfg.ListOpt(
            "index_url",
            default=["https://index.stackstorm.org/v1/index.json"],
            help="A URL pointing to the pack index. StackStorm Exchange is used by "
            "default. Use a comma-separated list for multiple indexes if you "
            'want to get other packs discovered with "st2 pack search".',
        ),
    ]

    do_register_opts(content_opts, "content", ignore_errors)

    webui_opts = [
        cfg.StrOpt(
            "webui_base_url",
            default="https://%s" % socket.getfqdn(),
            sample_default="https://localhost",
            help="Base https URL to access st2 Web UI. This is used to construct history URLs "
            "that are sent out when chatops is used to kick off executions.",
        )
    ]

    do_register_opts(webui_opts, "webui", ignore_errors)

    db_opts = [
        cfg.StrOpt("host", default="127.0.0.1", help="host of db server"),
        cfg.IntOpt("port", default=27017, help="port of db server"),
        cfg.StrOpt("db_name", default="st2", help="name of database"),
        cfg.StrOpt("username", help="username for db login"),
        cfg.StrOpt("password", help="password for db login", secret=True),
        cfg.IntOpt(
            "connection_timeout",
            default=3 * 1000,
            help="Connection and server selection timeout (in ms).",
        ),
        cfg.IntOpt(
            "connection_retry_max_delay_m",
            default=3,
            help="Connection retry total time (minutes).",
        ),
        cfg.IntOpt(
            "connection_retry_backoff_max_s",
            default=10,
            help="Connection retry backoff max (seconds).",
        ),
        cfg.IntOpt(
            "connection_retry_backoff_mul",
            default=1,
            help="Backoff multiplier (seconds).",
        ),
        cfg.BoolOpt(
            "tls",
            deprecated_name="ssl",
            default=False,
            help="Create the connection to mongodb using TLS.",
        ),
        cfg.StrOpt(
            "tls_certificate_key_file",
            default=None,
            help=(
                "Client certificate used to identify the local connection against MongoDB. "
                "The certificate file must contain one or both of private key and certificate. "
                "Supplying separate files for private key (ssl_keyfile) and certificate (ssl_certfile) "
                "is no longer supported. "
                "If encrypted, pass the password or passphrase in tls_certificate_key_file_password."
            ),
        ),
        cfg.StrOpt(
            "tls_certificate_key_file_password",
            default=None,
            help=(
                "The password or passphrase to decrypt the file in tls_certificate_key_file. "
                "Only set this if tls_certificate_key_file is encrypted."
            ),
            secret=True,
        ),
        cfg.StrOpt(
            "ssl_keyfile",
            default=None,
            help="Private keyfile used to identify the local connection against MongoDB.",
            deprecated_for_removal=True,
            deprecated_reason=(
                "Use tls_certificate_key_file with a path to a file containing "
                "the concatenation of the files from ssl_keyfile and ssl_certfile. "
                "This option is ignored by pymongo."
            ),
            deprecated_since="3.9.0",
        ),
        cfg.StrOpt(
            "ssl_certfile",
            default=None,
            help="Certificate file used to identify the localconnection",
            deprecated_for_removal=True,
            deprecated_reason=(
                "Use tls_certificate_key_file with a path to a file containing "
                "the concatenation of the files from ssl_keyfile and ssl_certfile. "
                "This option is ignored by pymongo. "
            ),
            deprecated_since="3.9.0",
        ),
        cfg.BoolOpt(
            "tls_allow_invalid_certificates",
            default=None,
            sample_default=False,
            help=(
                "Specifies whether MongoDB is allowed to pass an invalid certificate. "
                "This defaults to False to have security by default. "
                "Only temporarily set to True if you need to debug the connection."
            ),
        ),
        cfg.StrOpt(
            "ssl_cert_reqs",
            default=None,
            choices=["none", "optional", "required"],
            help=(
                "Specifies whether a certificate is required from the other side of the "
                "connection, and whether it will be validated if provided"
            ),
            deprecated_for_removal=True,
            deprecated_reason=(
                "Use tls_allow_invalid_certificates with the following: "
                "The 'optional' and 'required' values are equivalent to tls_allow_invalid_certificates=False. "
                "The 'none' value is equivalent to tls_allow_invalid_certificates=True. "
                "This option is a needlessly more complex version of tls_allow_invalid_certificates."
            ),
            deprecated_since="3.9.0",
        ),
        cfg.StrOpt(
            "tls_ca_file",
            deprecated_name="ssl_ca_certs",
            default=None,
            help=(
                "ca_certs file contains a set of concatenated CA certificates, which are "
                "used to validate certificates passed from MongoDB."
            ),
        ),
        cfg.BoolOpt(
            "tls_allow_invalid_hostnames",
            default=None,
            sample_default=False,
            help=(
                "If True and `tlsAllowInvalidCertificates` is True, disables hostname verification. "
                "This defaults to False to have security by default. "
                "Only temporarily set to True if you need to debug the connection."
            ),
        ),
        cfg.BoolOpt(
            "ssl_match_hostname",
            default=True,
            help="If True and `ssl_cert_reqs` is not None, enables hostname verification",
            deprecated_for_removal=True,
            deprecated_reason="Use tls_allow_invalid_hostnames with the opposite value from this option.",
            deprecated_since="3.9.0",
        ),
        cfg.StrOpt(
            "authentication_mechanism",
            default=None,
            help="Specifies database authentication mechanisms. "
            "By default, it use SCRAM-SHA-1 with MongoDB 3.0 and later, "
            "MONGODB-CR (MongoDB Challenge Response protocol) for older servers.",
        ),
        cfg.StrOpt(
            "compressors",
            default="",
            help="Comma delimited string of compression algorithms to use for transport level "
            "compression. Actual algorithm will then be decided based on the algorithms "
            "supported by the client and the server. For example: zstd. Defaults to no "
            "compression. Keep in mind that zstd is only supported with MongoDB 4.2 and later.",
        ),
        cfg.IntOpt(
            "zlib_compression_level",
            default="",
            help="Compression level when compressors is set to zlib. Valid values are -1 to 9. "
            "Defaults to 6.",
        ),
    ]

    do_register_opts(db_opts, "database", ignore_errors)

    messaging_opts = [
        # It would be nice to be able to deprecate url and completely switch to using
        # url. However, this will be a breaking change and will have impact so allowing both.
        cfg.StrOpt(
            "url",
            default="amqp://guest:guest@127.0.0.1:5672//",
            help="URL of the messaging server.",
        ),
        cfg.ListOpt(
            "cluster_urls",
            default=[],
            help="URL of all the nodes in a messaging service cluster.",
        ),
        cfg.IntOpt(
            "connection_retries",
            default=10,
            help="How many times should we retry connection before failing.",
        ),
        cfg.IntOpt(
            "connection_retry_wait",
            default=10000,
            help="How long should we wait between connection retries.",
        ),
        cfg.BoolOpt(
            "ssl",
            default=False,
            help="Use SSL / TLS to connect to the messaging server. Same as "
            'appending "?ssl=true" at the end of the connection URL string.',
        ),
        cfg.StrOpt(
            "ssl_keyfile",
            default=None,
            help="Private keyfile used to identify the local connection against RabbitMQ.",
        ),
        cfg.StrOpt(
            "ssl_certfile",
            default=None,
            help="Certificate file used to identify the local connection (client).",
        ),
        cfg.StrOpt(
            "ssl_cert_reqs",
            default=None,
            choices=["none", "optional", "required"],
            help="Specifies whether a certificate is required from the other side of the "
            "connection, and whether it will be validated if provided.",
        ),
        cfg.StrOpt(
            "ssl_ca_certs",
            default=None,
            help="ca_certs file contains a set of concatenated CA certificates, which are "
            "used to validate certificates passed from RabbitMQ.",
        ),
        cfg.StrOpt(
            "login_method",
            default=None,
            help="Login method to use (AMQPLAIN, PLAIN, EXTERNAL, etc.).",
        ),
        cfg.StrOpt(
            "compression",
            default=None,
            choices=["zstd", "lzma", "bz2", "gzip", None],
            help="Compression algorithm to use for compressing the payloads which are sent over "
            "the message bus. Defaults to no compression.",
        ),
        cfg.StrOpt(
            "prefix",
            default="st2",
            help="Prefix for all exchange and queue names.",
        ),
    ]

    do_register_opts(messaging_opts, "messaging", ignore_errors)

    syslog_opts = [
        cfg.StrOpt("host", default="127.0.0.1", help="Host for the syslog server."),
        cfg.IntOpt("port", default=514, help="Port for the syslog server."),
        cfg.StrOpt("facility", default="local7", help="Syslog facility level."),
        cfg.StrOpt(
            "protocol", default="udp", help="Transport protocol to use (udp / tcp)."
        ),
    ]

    do_register_opts(syslog_opts, "syslog", ignore_errors)

    log_opts = [
        cfg.ListOpt("excludes", default="", help="Exclusion list of loggers to omit."),
        cfg.BoolOpt(
            "redirect_stderr",
            default=False,
            help="Controls if stderr should be redirected to the logs.",
        ),
        cfg.BoolOpt(
            "mask_secrets", default=True, help="True to mask secrets in the log files."
        ),
        cfg.ListOpt(
            "mask_secrets_blacklist",
            default=[],
            help="Blacklist of additional attribute names to mask in the log messages.",
        ),
    ]

    do_register_opts(log_opts, "log", ignore_errors)

    # Common API options
    api_opts = [
        cfg.StrOpt("host", default="127.0.0.1", help="StackStorm API server host"),
        cfg.IntOpt("port", default=9101, help="StackStorm API server port"),
        cfg.ListOpt(
            "allow_origin",
            default=["http://127.0.0.1:3000"],
            help="List of origins allowed for api, auth and stream",
        ),
        cfg.IntOpt(
            "max_page_size",
            default=100,
            help="Maximum limit (page size) argument which can be specified by the "
            "user in a query string.",
        ),
        cfg.BoolOpt(
            "mask_secrets",
            default=True,
            help="True to mask secrets in the API responses",
        ),
        cfg.BoolOpt(
            "auth_cookie_secure",
            default=True,
            help='True if secure flag should be set for "auth-token" cookie which is set on '
            "successful authentication via st2web. You should only set this to False if you have "
            "a good reason to not run and access StackStorm behind https proxy.",
        ),
        cfg.StrOpt(
            "auth_cookie_same_site",
            default="lax",
            choices=["strict", "lax", "none", "unset"],
            help="SameSite attribute value for the "
            "auth-token cookie we set on successful authentication from st2web. If you "
            "don't have a specific reason (e.g. supporting old browsers) we recommend you "
            'set this value to strict. Setting it to "unset" will default to the behavior '
            "in previous releases and not set this SameSite header value.",
        ),
    ]

    do_register_opts(api_opts, "api", ignore_errors)

    # Key Value store options
    keyvalue_opts = [
        cfg.BoolOpt(
            "enable_encryption",
            default=True,
            help='Allow encryption of values in key value stored qualified as "secret".',
        ),
        cfg.StrOpt(
            "encryption_key_path",
            default="",
            help="Location of the symmetric encryption key for encrypting values in kvstore. "
            "This key should be in JSON and should've been generated using "
            "st2-generate-symmetric-crypto-key tool.",
        ),
    ]

    do_register_opts(keyvalue_opts, group="keyvalue")

    # Common auth options
    auth_opts = [
        cfg.StrOpt(
            "api_url",
            default=None,
            help="Base URL to the API endpoint excluding the version",
        ),
        cfg.BoolOpt("enable", default=True, help="Enable authentication middleware."),
        cfg.IntOpt(
            "token_ttl", default=(24 * 60 * 60), help="Access token ttl in seconds."
        ),
        # This TTL is used for tokens which belong to StackStorm services
        cfg.IntOpt(
            "service_token_ttl",
            default=(24 * 60 * 60),
            help="Service token ttl in seconds.",
        ),
    ]

    do_register_opts(auth_opts, "auth", ignore_errors)

    # Runner options
    default_python_bin_path = sys.executable
    # If the virtualenv uses a symlinked python, then try using virtualenv from that venv
    # first before looking for virtualenv installed in python's system-site-packages.
    base_dir = os.path.dirname(default_python_bin_path)
    default_virtualenv_bin_path = os.path.join(base_dir, "virtualenv")
    if not os.path.exists(default_virtualenv_bin_path):
        base_dir = os.path.dirname(os.path.realpath(default_python_bin_path))
        default_virtualenv_bin_path = os.path.join(base_dir, "virtualenv")

    action_runner_opts = [
        # Common runner options
        cfg.StrOpt(
            "logging",
            default="/etc/st2/logging.actionrunner.conf",
            help="location of the logging.conf file",
        ),
        # Python runner options
        cfg.StrOpt(
            "python_binary",
            default=default_python_bin_path,
            sample_default="/usr/bin/python3",
            help="Python binary which will be used by Python actions.",
        ),
        cfg.StrOpt(
            "virtualenv_binary",
            default=default_virtualenv_bin_path,
            sample_default="/usr/bin/virtualenv",
            help="Virtualenv binary which should be used to create pack virtualenvs.",
        ),
        cfg.StrOpt(
            "python_runner_log_level",
            default=PYTHON_RUNNER_DEFAULT_LOG_LEVEL,
            help="Default log level to use for Python runner actions. Can be overriden on "
            'invocation basis using "log_level" runner parameter.',
        ),
        cfg.ListOpt(
            "virtualenv_opts",
            default=["--system-site-packages"],
            help='List of virtualenv options to be passsed to "virtualenv" command that '
            "creates pack virtualenv.",
        ),
        cfg.ListOpt(
            "pip_opts",
            default=[],
            help='List of pip options to be passed to "pip install" command when installing pack '
            "dependencies into pack virtual environment.",
        ),
        cfg.BoolOpt(
            "stream_output",
            default=True,
            help="True to store and stream action output (stdout and stderr) in real-time.",
        ),
        cfg.IntOpt(
            "stream_output_buffer_size",
            default=-1,
            help=(
                "Buffer size to use for real time action output streaming. 0 means unbuffered "
                "1 means line buffered, -1 means system default, which usually means fully "
                "buffered and any other positive value means use a buffer of (approximately) "
                "that size"
            ),
        ),
    ]

    do_register_opts(
        action_runner_opts, group="actionrunner", ignore_errors=ignore_errors
    )

    dispatcher_pool_opts = [
        cfg.IntOpt(
            "workflows_pool_size",
            default=40,
            help="Internal pool size for dispatcher used by workflow actions.",
        ),
        cfg.IntOpt(
            "actions_pool_size",
            default=60,
            help="Internal pool size for dispatcher used by regular actions.",
        ),
    ]

    do_register_opts(
        dispatcher_pool_opts, group="actionrunner", ignore_errors=ignore_errors
    )

    graceful_shutdown_opts = [
        cfg.BoolOpt(
            "graceful_shutdown",
            default=True,
            help="This will enable the graceful shutdown and wait for ongoing requests to complete until exit_timeout.",
        ),
        cfg.IntOpt(
            "exit_still_active_check",
            default=300,
            help="How long to wait for process (in seconds) to exit after receiving shutdown signal.",
        ),
        cfg.IntOpt(
            "still_active_check_interval",
            default=2,
            help="Time interval between subsequent queries to check running executions.",
        ),
    ]

    do_register_opts(
        graceful_shutdown_opts, group="actionrunner", ignore_errors=ignore_errors
    )

    ssh_runner_opts = [
        cfg.StrOpt(
            "remote_dir",
            default="/tmp",
            help="Location of the script on the remote filesystem.",
        ),
        cfg.BoolOpt(
            "allow_partial_failure",
            default=False,
            help="How partial success of actions run on multiple nodes should be treated.",
        ),
        cfg.IntOpt(
            "max_parallel_actions",
            default=50,
            help="Max number of parallel remote SSH actions that should be run. "
            "Works only with Paramiko SSH runner.",
        ),
        cfg.BoolOpt(
            "use_ssh_config",
            default=False,
            help="Use the .ssh/config file. Useful to override ports etc.",
        ),
        cfg.StrOpt(
            "ssh_config_file_path",
            default="~/.ssh/config",
            help="Path to the ssh config file.",
        ),
        cfg.IntOpt(
            "ssh_connect_timeout",
            default=60,
            help="Max time in seconds to establish the SSH connection.",
        ),
    ]

    do_register_opts(ssh_runner_opts, group="ssh_runner", ignore_errors=ignore_errors)

    # Common options (used by action runner and sensor container)
    action_sensor_opts = [
        cfg.BoolOpt(
            "enable",
            default=True,
            help="Whether to enable or disable the ability to post a trigger on action.",
        ),
        cfg.ListOpt(
            "emit_when",
            default=LIVEACTION_COMPLETED_STATES,
            help="List of execution statuses for which a trigger will be emitted. ",
        ),
    ]

    do_register_opts(
        action_sensor_opts, group="action_sensor", ignore_errors=ignore_errors
    )

    # Common options for content
    pack_lib_opts = [
        cfg.BoolOpt(
            "enable_common_libs",
            default=False,
            help="Enable/Disable support for pack common libs. "
            "Setting this config to ``True`` would allow you to "
            "place common library code for sensors and actions in lib/ folder "
            "in packs and use them in python sensors and actions. "
            "See https://docs.stackstorm.com/reference/"
            "sharing_code_sensors_actions.html "
            "for details.",
        )
    ]

    do_register_opts(pack_lib_opts, group="packs", ignore_errors=ignore_errors)

    # Coordination options
    coord_opts = [
        cfg.StrOpt("url", default=None, help="Endpoint for the coordination server."),
        cfg.IntOpt(
            "lock_timeout", default=60, help="TTL for the lock if backend suports it."
        ),
        cfg.BoolOpt(
            "service_registry",
            default=False,
            help="True to register StackStorm services in a service registry.",
        ),
    ]

    do_register_opts(coord_opts, "coordination", ignore_errors)

    # XXX: This is required for us to support deprecated config group results_tracker
    query_opts = [
        cfg.IntOpt(
            "thread_pool_size",
            help="Number of threads to use to query external workflow systems.",
        ),
        cfg.FloatOpt(
            "query_interval",
            help="Time interval between subsequent queries for a context "
            "to external workflow system.",
        ),
    ]

    do_register_opts(query_opts, group="results_tracker", ignore_errors=ignore_errors)

    # Common stream options
    stream_opts = [
        cfg.IntOpt(
            "heartbeat",
            default=25,
            help="Send empty message every N seconds to keep connection open",
        )
    ]

    do_register_opts(stream_opts, group="stream", ignore_errors=ignore_errors)

    # Common CLI options
    cli_opts = [
        cfg.BoolOpt(
            "debug",
            default=False,
            help="Enable debug mode. By default this will set all log levels to DEBUG.",
        ),
        cfg.BoolOpt(
            "profile",
            default=False,
            help="Enable profile mode. In the profile mode all the MongoDB queries and "
            "related profile data are logged.",
        ),
        cfg.BoolOpt(
            "use-debugger",
            default=True,
            help="Enables debugger. Note that using this option changes how the "
            "eventlet library is used to support async IO. This could result in "
            "failures that do not occur under normal operation.",
        ),
        cfg.BoolOpt(
            "enable-profiler",
            default=False,
            help="Enable code profiler mode. Do not use in production.",
        ),
        cfg.BoolOpt(
            "enable-eventlet-blocking-detection",
            default=False,
            help="Enable eventlet blocking detection logic. Do not use in production.",
        ),
        cfg.FloatOpt(
            "eventlet-blocking-detection-resolution",
            default=0.5,
            help="Resolution in seconds for eventlet blocking detection logic.",
        ),
    ]

    do_register_cli_opts(cli_opts, ignore_errors=ignore_errors)

    # Metrics Options stream options
    metrics_opts = [
        cfg.StrOpt(
            "driver", default="noop", help="Driver type for metrics collection."
        ),
        cfg.StrOpt(
            "host",
            default="127.0.0.1",
            help="Destination server to connect to if driver requires connection.",
        ),
        cfg.IntOpt(
            "port",
            default=8125,
            help="Destination port to connect to if driver requires connection.",
        ),
        cfg.StrOpt(
            "prefix",
            default=None,
            help="Optional prefix which is prepended to all the metric names. Comes handy when "
            "you want to submit metrics from various environment to the same metric "
            "backend instance.",
        ),
        cfg.FloatOpt(
            "sample_rate",
            default=1,
            help="Randomly sample and only send metrics for X% of metric operations to the "
            "backend. Default value of 1 means no sampling is done and all the metrics are "
            "sent to the backend. E.g. 0.1 would mean 10% of operations are sampled.",
        ),
    ]

    do_register_opts(metrics_opts, group="metrics", ignore_errors=ignore_errors)

    # Common timers engine options
    timer_logging_opts = [
        cfg.StrOpt(
            "logging",
            default=None,
            help="Location of the logging configuration file. "
            "NOTE: Deprecated in favor of timersengine.logging",
        ),
    ]

    timers_engine_logging_opts = [
        cfg.StrOpt(
            "logging",
            default="/etc/st2/logging.timersengine.conf",
            help="Location of the logging configuration file.",
        )
    ]

    do_register_opts(timer_logging_opts, group="timer", ignore_errors=ignore_errors)
    do_register_opts(
        timers_engine_logging_opts, group="timersengine", ignore_errors=ignore_errors
    )

    # NOTE: We default old style deprecated "timer" options to None so our code
    # works correclty and "timersengine" has precedence over "timers"
    # NOTE: "timer" section will be removed in v3.1
    timer_opts = [
        cfg.StrOpt(
            "local_timezone",
            default=None,
            help="Timezone pertaining to the location where st2 is run. "
            "NOTE: Deprecated in favor of timersengine.local_timezone",
        ),
        cfg.BoolOpt(
            "enable",
            default=None,
            help="Specify to enable timer service. "
            "NOTE: Deprecated in favor of timersengine.enable",
        ),
    ]

    timers_engine_opts = [
        cfg.StrOpt(
            "local_timezone",
            default="America/Los_Angeles",
            help="Timezone pertaining to the location where st2 is run.",
        ),
        cfg.BoolOpt("enable", default=True, help="Specify to enable timer service."),
    ]
    do_register_opts(timer_opts, group="timer", ignore_errors=ignore_errors)
    do_register_opts(
        timers_engine_opts, group="timersengine", ignore_errors=ignore_errors
    )

    # Workflow engine options
    workflow_engine_opts = [
        cfg.IntOpt(
            "retry_stop_max_msec", default=60000, help="Max time to stop retrying."
        ),
        cfg.IntOpt(
            "retry_wait_fixed_msec", default=1000, help="Interval inbetween retries."
        ),
        cfg.FloatOpt(
            "retry_max_jitter_msec",
            default=1000,
            help="Max jitter interval to smooth out retries.",
        ),
        cfg.IntOpt(
            "gc_max_idle_sec",
            default=0,
            help="Max seconds to allow workflow execution be idled before it is identified as "
            "orphaned and cancelled by the garbage collector. A value of zero means the "
            "feature is disabled. This is disabled by default.",
        ),
        cfg.IntOpt(
            "exit_still_active_check",
            default=300,
            help="How long to wait for process (in seconds) to exit after receiving shutdown signal.",
        ),
        cfg.IntOpt(
            "still_active_check_interval",
            default=2,
            help="Time interval between subsequent queries to check executions handled by WFE.",
        ),
    ]

    do_register_opts(
        workflow_engine_opts, group="workflow_engine", ignore_errors=ignore_errors
    )


class St2EnvironmentConfigurationSource(EnvironmentConfigurationSource):
    @staticmethod
    def get_name(group_name, option_name):
        group_name = group_name or "DEFAULT"
        return "ST2_{}__{}".format(group_name.upper(), option_name.upper())


def use_st2_env_vars(conf: cfg.ConfigOpts) -> None:
    # Override oslo_config's 'OS_' env var prefix with 'ST2_'.
    conf._env_driver = St2EnvironmentConfigurationSource()


def parse_args(args=None, ignore_errors=False):
    use_st2_env_vars(cfg.CONF)
    register_opts(ignore_errors=ignore_errors)
    cfg.CONF(
        args=args,
        version=VERSION_STRING,
        default_config_files=[DEFAULT_CONFIG_FILE_PATH],
    )
