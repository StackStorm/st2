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

"""
This module contains common service setup and teardown code.
"""

from __future__ import absolute_import

import os
import sys
import traceback
import locale
import logging as stdlib_logging

import six
import eventlet.debug
from oslo_config import cfg
from tooz.coordination import GroupAlreadyExist
from tooz.coordination import GroupNotCreated
from tooz.coordination import MemberNotJoined

from st2common import log as logging
from st2common.constants.logging import DEFAULT_LOGGING_CONF_PATH
from st2common.transport.bootstrap_utils import register_exchanges_with_retry
from st2common.transport.bootstrap_utils import register_kombu_serializers
from st2common.bootstrap import runnersregistrar
from st2common.signal_handlers import register_common_signal_handlers
from st2common.util.debugging import enable_debugging
from st2common.models.utils.profiling import enable_profiling
from st2common import triggers
from st2common.rbac.migrations import run_all as run_all_rbac_migrations
from st2common.logging.filters import LogLevelFilter
from st2common.util import system_info
from st2common.services import coordination
from st2common.logging.misc import add_global_filters_for_all_loggers
from st2common.constants.error_messages import PYTHON2_DEPRECATION
from st2common.services.coordination import get_driver_name
from st2common.util.profiler import setup_eventlet_profiler

# Note: This is here for backward compatibility.
# Function has been moved in a standalone module to avoid expensive in-direct
# import costs
from st2common.database_setup import db_setup
from st2common.database_setup import db_teardown
from st2common.metrics.base import metrics_initialize


__all__ = [
    "setup",
    "teardown",
    "db_setup",
    "db_teardown",
    "register_service_in_service_registry",
    "deregister_service",
]

# Message which is logged if non utf-8 locale is detected on startup.
NON_UTF8_LOCALE_WARNING_MSG = """
Detected a non utf-8 locale / encoding (fs encoding: %s, default encoding: %s, locale: %s).
Using non utf-8 locale while working with unicode data will result in exceptions and undefined
behavior.
You are strongly encouraged to configure all the StackStorm services to use utf-8 encoding (e.g.
LANG=en_US.UTF-8).
""".strip().replace(
    "\n", " "
)

VALID_UTF8_ENCODINGS = ["utf8", "utf-8"]

LOG = logging.getLogger(__name__)


def setup(
    service,
    config,
    setup_db=True,
    register_mq_exchanges=True,
    register_signal_handlers=True,
    register_internal_trigger_types=False,
    run_migrations=True,
    register_runners=True,
    service_registry=False,
    capabilities=None,
    config_args=None,
):
    """
    Common setup function.

    Currently it performs the following operations:

    1. Parses config and CLI arguments
    2. Establishes DB connection
    3. Set log level for all the loggers to DEBUG if --debug flag is present or
       if system.debug config option is set to True.
    4. Registers RabbitMQ exchanges
    5. Registers common signal handlers
    6. Register internal trigger types
    7. Register all the runners which are installed inside StackStorm virtualenv.
    8. Register service in the service registry with the provided capabilities

    :param service: Name of the service.
    :param config: Config object to use to parse args.
    """
    capabilities = capabilities or {}

    # Set up logger which logs everything which happens during and before config
    # parsing to sys.stdout
    logging.setup(DEFAULT_LOGGING_CONF_PATH, excludes=None)

    # Parse args to setup config.
    if config_args is not None:
        config.parse_args(config_args)
    else:
        config.parse_args()

    if cfg.CONF.enable_profiler:
        setup_eventlet_profiler(service_name="st2" + service)

    version = "%s.%s.%s" % (
        sys.version_info[0],
        sys.version_info[1],
        sys.version_info[2],
    )

    # We print locale related info to make it easier to troubleshoot issues where locale is not
    # set correctly (e.g. using C / ascii, but services are trying to work with unicode data
    # would result in things blowing up)

    fs_encoding = sys.getfilesystemencoding()
    default_encoding = sys.getdefaultencoding()
    lang_env = os.environ.get("LANG", "unknown")
    lang_env = os.environ.get("LANG", "notset")
    pythonioencoding_env = os.environ.get("PYTHONIOENCODING", "notset")

    try:
        language_code, encoding = locale.getdefaultlocale()

        if language_code and encoding:
            used_locale = ".".join([language_code, encoding])
        else:
            used_locale = "unable to retrieve locale"
    except Exception as e:
        used_locale = "unable to retrieve locale: %s " % (str(e))
        encoding = "unknown"

    LOG.info("Using Python: %s (%s)" % (version, sys.executable))
    LOG.info(
        "Using fs encoding: %s, default encoding: %s, locale: %s, LANG env variable: %s, "
        "PYTHONIOENCODING env variable: %s"
        % (fs_encoding, default_encoding, lang_env, used_locale, pythonioencoding_env)
    )

    config_file_paths = cfg.CONF.config_file
    config_file_paths = [os.path.abspath(path) for path in config_file_paths]
    LOG.info("Using config files: %s", ",".join(config_file_paths))

    # Setup logging.
    logging_config_path = config.get_logging_config_path()
    logging_config_path = os.path.abspath(logging_config_path)

    LOG.info("Using logging config: %s", logging_config_path)
    LOG.info("Using coordination driver: %s", get_driver_name())
    LOG.info("Using metrics driver: %s", cfg.CONF.metrics.driver)

    # Warn on non utf-8 locale which could cause issues when running under Python 3 and working
    # with unicode data
    if (
        fs_encoding.lower() not in VALID_UTF8_ENCODINGS
        or encoding.lower() not in VALID_UTF8_ENCODINGS
    ):
        LOG.warning(
            NON_UTF8_LOCALE_WARNING_MSG
            % (fs_encoding, default_encoding, used_locale.strip())
        )

    is_debug_enabled = cfg.CONF.debug or cfg.CONF.system.debug

    try:
        logging.setup(
            logging_config_path,
            redirect_stderr=cfg.CONF.log.redirect_stderr,
            excludes=cfg.CONF.log.excludes,
        )
    except KeyError as e:
        tb_msg = traceback.format_exc()
        if "log.setLevel" in tb_msg:
            msg = (
                "Invalid log level selected. Log level names need to be all uppercase."
            )
            msg += "\n\n" + getattr(e, "message", six.text_type(e))
            raise KeyError(msg)
        else:
            raise e

    exclude_log_levels = [stdlib_logging.AUDIT]
    handlers = stdlib_logging.getLoggerClass().manager.root.handlers

    for handler in handlers:
        # If log level is not set to DEBUG we filter out "AUDIT" log messages. This way we avoid
        # duplicate "AUDIT" messages in production deployments where default service log level is
        # set to "INFO" and we already log messages with level AUDIT to a special dedicated log
        # file.
        ignore_audit_log_messages = (
            handler.level >= stdlib_logging.INFO
            and handler.level < stdlib_logging.AUDIT
        )
        if not is_debug_enabled and ignore_audit_log_messages:
            try:
                handler_repr = str(handler)
            except TypeError:
                # In case handler doesn't have name assigned, repr would throw
                handler_repr = "unknown"

            LOG.debug(
                'Excluding log messages with level "AUDIT" for handler "%s"'
                % (handler_repr)
            )
            handler.addFilter(LogLevelFilter(log_levels=exclude_log_levels))

    if not is_debug_enabled:
        # NOTE: statsd logger logs everything by default under INFO so we ignore those log
        # messages unless verbose / debug mode is used
        logging.ignore_statsd_log_messages()

    logging.ignore_lib2to3_log_messages()

    if is_debug_enabled:
        enable_debugging()
    else:
        # Add global ignore filters, such as "heartbeat_tick" messages which are logged every 2
        # ms which cause too much noise
        add_global_filters_for_all_loggers()

    if cfg.CONF.profile:
        enable_profiling()

    # All other setup which requires config to be parsed and logging to be correctly setup.
    if setup_db:
        db_setup()

    if register_mq_exchanges:
        register_exchanges_with_retry()

    if register_signal_handlers:
        register_common_signal_handlers()

    if register_internal_trigger_types:
        triggers.register_internal_trigger_types()

    # TODO: This is a "not so nice" workaround until we have a proper migration system in place
    if run_migrations:
        run_all_rbac_migrations()

    if register_runners:
        runnersregistrar.register_runners()

    register_kombu_serializers()

    metrics_initialize()

    # Register service in the service registry
    if cfg.CONF.coordination.service_registry and service_registry:
        # NOTE: It's important that we pass start_heart=True to start the hearbeat process
        register_service_in_service_registry(
            service=service, capabilities=capabilities, start_heart=True
        )

    if sys.version_info[0] == 2:
        LOG.warning(PYTHON2_DEPRECATION)

    # NOTE: This must be called here at the end of the setup phase since some of the setup code and
    # modules like jinja, stevedore, etc load files from disk on init which is slow and will be
    # detected as blocking operation, but this is not really an issue inside the service startup /
    # init phase.
    if cfg.CONF.enable_eventlet_blocking_detection:
        print("Eventlet long running / blocking operation detection logic enabled")
        print(cfg.CONF.eventlet_blocking_detection_resolution)
        eventlet.debug.hub_blocking_detection(
            state=True, resolution=cfg.CONF.eventlet_blocking_detection_resolution
        )


def teardown():
    """
    Common teardown function.
    """
    # 1. Tear down the database
    db_teardown()

    # 2. Tear down the coordinator
    coordinator = coordination.get_coordinator_if_set()
    coordination.coordinator_teardown(coordinator)


def register_service_in_service_registry(service, capabilities=None, start_heart=True):
    """
    Register provided service in the service registry and start the heartbeat process.

    :param service: Service name which will also be used for a group name (e.g. "api").
    :type service: ``str``

    :param capabilities: Optional metadata associated with the service.
    :type capabilities: ``dict``
    """
    # NOTE: It's important that we pass start_heart=True to start the hearbeat process
    coordinator = coordination.get_coordinator(start_heart=start_heart)

    member_id = coordination.get_member_id()

    # 1. Create a group with the name of the service
    if not isinstance(service, six.binary_type):
        group_id = service.encode("utf-8")
    else:
        group_id = service

    try:
        coordinator.create_group(group_id).get()
    except GroupAlreadyExist:
        pass

    # Include common capabilities such as hostname and process ID
    proc_info = system_info.get_process_info()
    capabilities["hostname"] = proc_info["hostname"]
    capabilities["pid"] = proc_info["pid"]

    # 1. Join the group as a member
    LOG.debug(
        'Joining service registry group "%s" as member_id "%s" with capabilities "%s"'
        % (group_id, member_id, capabilities)
    )
    return coordinator.join_group(group_id, capabilities=capabilities).get()


def deregister_service(service, start_heart=True):

    if not isinstance(service, six.binary_type):
        group_id = service.encode("utf-8")
    else:
        group_id = service

    coordinator = coordination.get_coordinator(start_heart=start_heart)

    member_id = coordination.get_member_id()
    LOG.debug(
        'Leaving service registry group "%s" as member_id "%s"' % (group_id, member_id)
    )
    try:
        coordinator.leave_group(group_id).get()
    except (GroupNotCreated, MemberNotJoined):
        pass
