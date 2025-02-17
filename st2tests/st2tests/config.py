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
from typing import Dict

from oslo_config import cfg, types

from st2common import log as logging
import st2common.config as common_config
from st2common.constants.system import DEFAULT_CONFIG_FILE_PATH
from st2common.constants.garbage_collection import DEFAULT_COLLECTION_INTERVAL
from st2common.constants.garbage_collection import DEFAULT_SLEEP_DELAY
from st2common.constants.sensors import DEFAULT_PARTITION_LOADER
from st2tests.fixturesloader import get_fixtures_packs_base_path

CONF = cfg.CONF
LOG = logging.getLogger(__name__)

# Ued for tests. For majority of tests, we want this value to be False.
USE_DEFAULT_CONFIG_FILES = False


def reset():
    cfg.CONF.reset()


def parse_args(args=None, coordinator_noop=True):
    common_config.use_st2_env_vars(cfg.CONF)
    _setup_config_opts(coordinator_noop=coordinator_noop)

    kwargs = {}
    if USE_DEFAULT_CONFIG_FILES:
        kwargs["default_config_files"] = [DEFAULT_CONFIG_FILE_PATH]

    cfg.CONF(args=args or [], **kwargs)


def _setup_config_opts(coordinator_noop=True):
    reset()

    try:
        _register_config_opts()
    except Exception as e:
        print(e)
        # Some scripts register the options themselves which means registering them again will
        # cause a non-fatal exception
        return

    _override_config_opts(coordinator_noop=coordinator_noop)


def _override_config_opts(coordinator_noop=False):
    _override_db_opts()
    _override_mq_opts()
    _override_common_opts()
    _override_api_opts()
    _override_keyvalue_opts()
    _override_scheduler_opts()
    _override_workflow_engine_opts()
    _override_coordinator_opts(noop=coordinator_noop)


def _register_config_opts():
    _register_common_opts()
    _register_api_opts()
    _register_stream_opts()
    _register_auth_opts()
    _register_action_sensor_opts()
    _register_ssh_runner_opts()
    _register_scheduler_opts()
    _register_sensor_container_opts()
    _register_garbage_collector_opts()


def _override_db_opts():
    # use separate dbs for safer parallel test runs
    db_name = f"st2-test{os.environ.get('ST2TESTS_PARALLEL_SLOT', '')}"
    CONF.set_override(name="db_name", override=db_name, group="database")
    CONF.set_override(name="host", override="127.0.0.1", group="database")


def db_opts_as_env_vars() -> Dict[str, str]:
    env = {
        "ST2_DATABASE__HOST": CONF.database.host,
        "ST2_DATABASE__PORT": str(CONF.database.port),
        "ST2_DATABASE__DB_NAME": CONF.database.db_name,
        "ST2_DATABASE__CONNECTION_TIMEOUT": str(CONF.database.connection_timeout),
    }
    if CONF.database.username is not None:
        env["ST2_DATABASE__USERNAME"] = CONF.database.username
    if CONF.database.password is not None:
        env["ST2_DATABASE__PASSWORD"] = CONF.database.password
    return env


def _override_mq_opts():
    mq_prefix = CONF.messaging.prefix
    mq_prefix = "st2test" if mq_prefix == "st2" else mq_prefix
    mq_prefix = mq_prefix + os.environ.get("ST2TESTS_PARALLEL_SLOT", "")
    CONF.set_override(name="prefix", override=mq_prefix, group="messaging")


def mq_opts_as_env_vars() -> Dict[str, str]:
    return {
        "ST2_MESSAGING__URL": CONF.messaging.url,
        "ST2_MESSAGING__PREFIX": CONF.messaging.prefix,
    }


def _override_common_opts():
    packs_base_path = get_fixtures_packs_base_path()
    CONF.set_override(name="base_path", override=packs_base_path, group="system")
    CONF.set_override(name="validate_output_schema", override=True, group="system")
    CONF.set_override(
        name="system_packs_base_path", override=packs_base_path, group="content"
    )
    CONF.set_override(
        name="packs_base_paths", override=packs_base_path, group="content"
    )
    CONF.set_override(name="api_url", override="http://127.0.0.1", group="auth")
    CONF.set_override(name="mask_secrets", override=True, group="log")
    CONF.set_override(name="stream_output", override=False, group="actionrunner")
    system_user = os.environ.get("ST2TESTS_SYSTEM_USER", "")
    if system_user:
        CONF.set_override(name="user", override=system_user, group="system_user")


def _override_api_opts():
    CONF.set_override(
        name="allow_origin",
        override=["http://127.0.0.1:3000", "http://dev"],
        group="api",
    )
    CONF.set_override(
        name="auth_cookie_secure",
        override=False,
        group="api",
    )


def _override_keyvalue_opts():
    current_file_path = os.path.dirname(__file__)
    rel_st2_base_path = os.path.join(current_file_path, "../..")
    abs_st2_base_path = os.path.abspath(rel_st2_base_path)
    rel_enc_key_path = "st2tests/conf/st2_kvstore_tests.crypto.key.json"
    ovr_enc_key_path = os.path.join(abs_st2_base_path, rel_enc_key_path)
    CONF.set_override(
        name="encryption_key_path", override=ovr_enc_key_path, group="keyvalue"
    )


def _override_scheduler_opts():
    CONF.set_override(name="sleep_interval", group="scheduler", override=0.01)


def _override_coordinator_opts(noop=False):
    driver = None if noop else "zake://"

    redis_host = os.environ.get("ST2TESTS_REDIS_HOST", False)
    if redis_host:
        redis_port = os.environ.get("ST2TESTS_REDIS_PORT", "6379")
        # namespace= is the tooz redis driver's key prefix (default is "_tooz")
        namespace = f"_st2_test{os.environ.get('ST2TESTS_PARALLEL_SLOT', '')}"
        driver = f"redis://{redis_host}:{redis_port}?namespace={namespace}"

    CONF.set_override(name="url", override=driver, group="coordination")
    CONF.set_override(name="lock_timeout", override=1, group="coordination")


def coord_opts_as_env_vars() -> Dict[str, str]:
    env = {}
    if CONF.coordination.url is not None:
        env["ST2_COORDINATION__URL"] = CONF.coordination.url
    return env


def _override_workflow_engine_opts():
    cfg.CONF.set_override("retry_stop_max_msec", 200, group="workflow_engine")
    cfg.CONF.set_override("retry_wait_fixed_msec", 100, group="workflow_engine")
    cfg.CONF.set_override("retry_max_jitter_msec", 100, group="workflow_engine")
    cfg.CONF.set_override("gc_max_idle_sec", 1, group="workflow_engine")


def _register_common_opts():
    try:
        common_config.register_opts(ignore_errors=True)
    except:
        LOG.exception("Common config registration failed.")


def _register_api_opts():
    # XXX: note : template_path value only works if started from the top-level of the codebase.
    # Brittle!
    pecan_opts = [
        cfg.StrOpt(
            "root",
            default="st2api.controllers.root.RootController",
            help="Pecan root controller",
        ),
        cfg.StrOpt("template_path", default="%(confdir)s/st2api/st2api/templates"),
        cfg.ListOpt("modules", default=["st2api"]),
        cfg.BoolOpt("debug", default=True),
        cfg.BoolOpt("auth_enable", default=True),
        cfg.DictOpt("errors", default={404: "/error/404", "__force_dict__": True}),
    ]

    _register_opts(pecan_opts, group="api_pecan")

    api_opts = [
        cfg.BoolOpt("debug", default=True),
    ]

    _register_opts(api_opts, group="api")

    messaging_opts = [
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
            "prefix",
            default="st2",
            help="Prefix for all exchange and queue names.",
        ),
    ]

    _register_opts(messaging_opts, group="messaging")

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
        cfg.BoolOpt(
            "use_ssh_config",
            default=False,
            help="Use the .ssh/config file. Useful to override ports etc.",
        ),
    ]

    _register_opts(ssh_runner_opts, group="ssh_runner")


def _register_stream_opts():
    stream_opts = [
        cfg.IntOpt(
            "heartbeat",
            default=25,
            help="Send empty message every N seconds to keep connection open",
        ),
        cfg.BoolOpt("debug", default=False, help="Specify to enable debug mode."),
    ]

    _register_opts(stream_opts, group="stream")


def _register_auth_opts():
    auth_opts = [
        cfg.StrOpt("host", default="127.0.0.1"),
        cfg.IntOpt("port", default=9100),
        cfg.BoolOpt("use_ssl", default=False),
        cfg.StrOpt("mode", default="proxy"),
        cfg.StrOpt("backend", default="flat_file"),
        cfg.StrOpt("backend_kwargs", default=None),
        cfg.StrOpt("logging", default="conf/logging.conf"),
        cfg.IntOpt("token_ttl", default=86400, help="Access token ttl in seconds."),
        cfg.BoolOpt("sso", default=True),
        cfg.StrOpt("sso_backend", default="noop"),
        cfg.StrOpt("sso_backend_kwargs", default=None),
        cfg.BoolOpt("debug", default=True),
    ]

    _register_opts(auth_opts, group="auth")


def _register_action_sensor_opts():
    action_sensor_opts = [
        cfg.BoolOpt(
            "enable",
            default=True,
            help="Whether to enable or disable the ability to post a trigger on action.",
        ),
        cfg.StrOpt(
            "triggers_base_url",
            default="http://127.0.0.1:9101/v1/triggertypes/",
            help="URL for action sensor to post TriggerType.",
        ),
        cfg.IntOpt(
            "request_timeout",
            default=1,
            help="Timeout value of all httprequests made by action sensor.",
        ),
        cfg.IntOpt(
            "max_attempts", default=10, help="No. of times to retry registration."
        ),
        cfg.IntOpt(
            "retry_wait",
            default=1,
            help="Amount of time to wait prior to retrying a request.",
        ),
    ]

    _register_opts(action_sensor_opts, group="action_sensor")


def _register_ssh_runner_opts():
    ssh_runner_opts = [
        cfg.BoolOpt(
            "use_ssh_config",
            default=False,
            help="Use the .ssh/config file. Useful to override ports etc.",
        ),
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
    ]

    _register_opts(ssh_runner_opts, group="ssh_runner")


def _register_scheduler_opts():
    scheduler_opts = [
        cfg.FloatOpt(
            "execution_scheduling_timeout_threshold_min",
            default=1,
            help="How long GC to search back in minutes for orphaned scheduled actions",
        ),
        cfg.IntOpt(
            "pool_size",
            default=10,
            help="The size of the pool used by the scheduler for scheduling executions.",
        ),
        cfg.FloatOpt(
            "sleep_interval",
            default=0.01,
            help="How long to sleep between each action scheduler main loop run interval (in ms).",
        ),
        cfg.FloatOpt(
            "gc_interval",
            default=5,
            help="How often to look for zombie executions before rescheduling them (in ms).",
        ),
        cfg.IntOpt(
            "retry_max_attempt",
            default=3,
            help="The maximum number of attempts that the scheduler retries on error.",
        ),
        cfg.IntOpt(
            "retry_wait_msec",
            default=100,
            help="The number of milliseconds to wait in between retries.",
        ),
    ]

    _register_opts(scheduler_opts, group="scheduler")


def _register_sensor_container_opts():
    partition_opts = [
        cfg.StrOpt(
            "sensor_node_name", default="sensornode1", help="name of the sensor node."
        ),
        cfg.Opt(
            "partition_provider",
            type=types.Dict(value_type=types.String()),
            default={"name": DEFAULT_PARTITION_LOADER},
            help="Provider of sensor node partition config.",
        ),
    ]

    _register_opts(partition_opts, group="sensorcontainer")

    # Other options
    other_opts = [
        cfg.BoolOpt(
            "single_sensor_mode",
            default=False,
            help="Run in a single sensor mode where parent process exits when a sensor crashes / "
            "dies. This is useful in environments where partitioning, sensor process life "
            "cycle and failover is handled by a 3rd party service such as kubernetes.",
        )
    ]

    _register_opts(other_opts, group="sensorcontainer")

    # CLI options
    cli_opts = [
        cfg.StrOpt(
            "sensor-ref",
            help="Only run sensor with the provided reference. Value is of the form "
            "<pack>.<sensor-name> (e.g. linux.FileWatchSensor).",
        ),
        cfg.BoolOpt(
            "single-sensor-mode",
            default=False,
            help="Run in a single sensor mode where parent process exits when a sensor crashes / "
            "dies. This is useful in environments where partitioning, sensor process life "
            "cycle and failover is handled by a 3rd party service such as kubernetes.",
        ),
    ]

    _register_cli_opts(cli_opts)


def _register_garbage_collector_opts():
    common_opts = [
        cfg.IntOpt(
            "collection_interval",
            default=DEFAULT_COLLECTION_INTERVAL,
            help="How often to check database for old data and perform garbage collection.",
        ),
        cfg.FloatOpt(
            "sleep_delay",
            default=DEFAULT_SLEEP_DELAY,
            help="How long to wait / sleep (in seconds) between "
            "collection of different object types.",
        ),
    ]

    _register_opts(common_opts, group="garbagecollector")

    ttl_opts = [
        cfg.IntOpt(
            "action_executions_ttl",
            default=None,
            help="Action executions and related objects (live actions, action output "
            "objects) older than this value (days) will be automatically deleted. Defaults to None (disabled).",
        ),
        cfg.IntOpt(
            "action_executions_output_ttl",
            default=7,
            help="Action execution output objects (ones generated by action output "
            "streaming) older than this value (days) will be automatically deleted. Defaults to 7.",
        ),
        cfg.IntOpt(
            "trigger_instances_ttl",
            default=None,
            help="Trigger instances older than this value (days) will be automatically deleted. Defaults to None (disabled).",
        ),
        cfg.IntOpt(
            "rule_enforcements_ttl",
            default=None,
            help="Rule enforcements older than this value (days) will be automatically deleted. Defaults to None (disabled).",
        ),
        cfg.IntOpt(
            "tokens_ttl",
            default=None,
            help="Tokens that expired over this value (days) will be automatically deleted. Defaults to None (disabled).",
        ),
        cfg.IntOpt(
            "traces_ttl",
            default=None,
            help="Trace objects older than this value (days) will be automatically deleted. Defaults to None (disabled).",
        ),
        cfg.IntOpt(
            "workflow_executions_ttl",
            default=None,
            help="Workflow execution output objects (generated by action output "
            "streaming) older than this value (days) will be automatically deleted. "
            "Defaults to None (disabled).",
        ),
        cfg.IntOpt(
            "task_executions_ttl",
            default=None,
            help="Workflow task execution output objects (generated by action output "
            "streaming) older than this value (days) will be automatically deleted. "
            "Defaults to None (disabled).",
        ),
    ]

    _register_opts(ttl_opts, group="garbagecollector")

    inquiry_opts = [
        cfg.BoolOpt(
            "purge_inquiries",
            default=False,
            help="Set to True to perform garbage collection on Inquiries (based on "
            "the TTL value per Inquiry)",
        )
    ]

    _register_opts(inquiry_opts, group="garbagecollector")


def _register_opts(opts, group=None):
    CONF.register_opts(opts, group)


def _register_cli_opts(opts):
    cfg.CONF.register_cli_opts(opts)
