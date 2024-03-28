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

import os.path
import logging

import six

from st2common.logging.filters import LoggerFunctionNameExclusionFilter

__all__ = [
    "reopen_log_files",
    "set_log_level_for_all_handlers",
    "set_log_level_for_all_loggers",
    "add_global_filters_for_all_loggers",
]

LOG = logging.getLogger(__name__)

# Because some loggers are just waste of attention span
SPECIAL_LOGGERS = {"swagger_spec_validator.ref_validators": logging.INFO}

# Log messages for function names which are very spammy and we want to filter out when DEBUG log
# level is enabled
IGNORED_FUNCTION_NAMES = [
    # Used by pyamqp, logs every heartbit tick every 2 ms by default
    "heartbeat_tick"
]

# List of global filters which apply to all the loggers
GLOBAL_FILTERS = [LoggerFunctionNameExclusionFilter(exclusions=IGNORED_FUNCTION_NAMES)]


def reopen_log_files(handlers):
    """
    This method iterates through all of the providers handlers looking for the FileHandler types.

    A lock is acquired, the underlying stream closed, reopened, then the lock is released.


    This method should be called when logs are to be rotated by an external process. The simplest
    way to do this is via a signal handler.
    """
    for handler in handlers:
        if not isinstance(handler, logging.FileHandler):
            continue

        LOG.info(
            'Re-opening log file "%s" with mode "%s"\n'
            % (handler.baseFilename, handler.mode)
        )

        try:
            handler.acquire()
            handler.stream.close()
            handler.stream = open(handler.baseFilename, handler.mode)
        finally:
            try:
                handler.release()
            except RuntimeError as e:
                if "cannot release" in six.text_type(e):
                    # Release failed which most likely indicates that acquire failed
                    # and lock was never acquired
                    LOG.warning("Failed to release lock", exc_info=True)
                else:
                    raise e


def set_log_level_for_all_handlers(logger, level=logging.DEBUG):
    """
    Set a log level for all the handlers on the provided logger.
    """
    logger.setLevel(level)

    handlers = logger.handlers
    for handler in handlers:
        handler.setLevel(level)

    return logger


def set_log_level_for_all_loggers(level=logging.DEBUG):
    """
    Set a log level for all the loggers and handlers to the provided level.
    """
    root_logger = logging.getLogger()
    loggers = list(logging.Logger.manager.loggerDict.values())
    loggers += [root_logger]

    for logger in loggers:
        if not isinstance(logger, logging.Logger):
            continue

        logger = add_filters_for_logger(logger=logger, filters=GLOBAL_FILTERS)

        if logger.name in SPECIAL_LOGGERS:
            set_log_level_for_all_handlers(
                logger=logger, level=SPECIAL_LOGGERS.get(logger.name)
            )
        else:
            set_log_level_for_all_handlers(logger=logger, level=level)

    return loggers


def add_global_filters_for_all_loggers():
    """
    Add global filters to all the loggers.

    This way we ensure "spamy" messages like heartbeat_tick are excluded also when --debug flag /
    system.debug config option is not set, but log level is set to DEBUG.
    """
    root_logger = logging.getLogger()
    loggers = list(logging.Logger.manager.loggerDict.values())
    loggers += [root_logger]

    for logger in loggers:
        if not isinstance(logger, logging.Logger):
            continue

        logger = add_filters_for_logger(logger=logger, filters=GLOBAL_FILTERS)

    return loggers


def add_filters_for_logger(logger, filters):
    """
    Add provided exclusion filters to the provided logger instance.

    :param logger: Logger class instance.
    :type logger: :class:`logging.Filter`

    :param filter: List of Logger filter instances.
    :type filter: ``list`` of :class:`logging.Filter`
    """
    if not isinstance(logger, logging.Logger):
        return logger

    if not hasattr(logger, "addFilter"):
        return logger

    for logger_filter in filters:
        logger.addFilter(logger_filter)

    return logger


def get_logger_name_for_module(module, exclude_module_name=False):
    """
    Retrieve fully qualified logger name for current module (e.g. st2common.cmd.sensormanager).

    :type: ``str``
    """
    module_file = module.__file__
    base_dir = os.path.dirname(os.path.abspath(module_file))
    module_name = os.path.basename(module_file)
    module_name = module_name.replace(".pyc", "").replace(".py", "")

    split = base_dir.split(os.path.sep)
    split = [component for component in split if component]

    # Find first component which starts with st2 and use that as a starting point
    start_index = 0
    for index, component in enumerate(reversed(split)):
        if component.startswith("st2"):
            start_index = (len(split) - 1) - index
            break

    split = split[start_index:]

    if exclude_module_name:
        name = ".".join(split)
    else:
        name = ".".join(split) + "." + module_name

    return name
