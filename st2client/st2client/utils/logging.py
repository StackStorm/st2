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

import logging

__all__ = [
    'LogLevelFilter',
    'set_log_level_for_all_handlers',
    'set_log_level_for_all_loggers'
]


class LogLevelFilter(logging.Filter):
    """
    Filter which excludes log messages which match the provided log levels.
    """

    def __init__(self, log_levels):
        self._log_levels = log_levels

    def filter(self, record):
        level = record.levelno
        if level in self._log_levels:
            return False

        return True


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

        set_log_level_for_all_handlers(logger=logger)
