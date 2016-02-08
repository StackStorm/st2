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

import os.path
import logging

__all__ = [
    'reopen_log_files',
    'set_log_level_for_all_handlers',
    'set_log_level_for_all_loggers'
]

LOG = logging.getLogger(__name__)


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

        LOG.info('Re-opening log file "%s" with mode "%s"\n' %
                 (handler.baseFilename, handler.mode))

        try:
            handler.acquire()
            handler.stream.close()
            handler.stream = open(handler.baseFilename, handler.mode)
        finally:
            try:
                handler.release()
            except RuntimeError as e:
                if 'cannot release' in str(e):
                    # Release failed which most likely indicates that acquire failed
                    # and lock was never acquired
                    LOG.warn('Failed to release lock', exc_info=True)
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
    loggers = logging.Logger.manager.loggerDict.values()
    loggers += [root_logger]

    for logger in loggers:
        if not isinstance(logger, logging.Logger):
            continue

        set_log_level_for_all_handlers(logger=logger)


def get_logger_name_for_module(module):
    """
    Retrieve fully qualified logger name for current module (e.g.
    st2common.cmd.sensormanager)

    :type: ``str``
    """
    module_file = module.__file__
    base_dir = os.path.dirname(os.path.abspath(module_file))
    module_name = os.path.basename(module_file)
    module_name = module_name.replace('.pyc', '').replace('.py', '')

    split = base_dir.split(os.path.sep)
    split = [component for component in split if component]

    # Find first component which starts with st2 and use that as a starting point
    start_index = 0
    for index, component in enumerate(reversed(split)):
        if component.startswith('st2'):
            start_index = ((len(split) - 1) - index)
            break

    split = split[start_index:]
    name = '.'.join(split) + '.' + module_name

    return name
