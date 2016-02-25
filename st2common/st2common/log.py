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
import sys
import logging
import logging.config
import logging.handlers
import traceback
from functools import wraps

import six

from st2common.logging.filters import ExclusionFilter

# Those are here for backward compatibility reasons
from st2common.logging.handlers import FormatNamedFileHandler
from st2common.logging.handlers import ConfigurableSyslogHandler
from st2common.util.misc import prefix_dict_keys
from st2common.util.misc import get_normalized_file_path

__all__ = [
    'getLogger',
    'setup',

    'FormatNamedFileHandler',
    'ConfigurableSyslogHandler',

    'LoggingStream'
]

logging.AUDIT = logging.CRITICAL + 10
logging.addLevelName(logging.AUDIT, 'AUDIT')

LOGGER_KEYS = [
    'debug',
    'info',
    'warning',
    'error',
    'critical',
    'exception',
    'log',

    'audit'
]

# Note: This attribute is used by "find_caller" so it can correctly exclude this file when looking
# for the logger method caller frame.
_srcfile = get_normalized_file_path(__file__)


def find_caller():
    """
    Find the stack frame of the caller so that we can note the source file name, line number and
    function name.

    Note: This is based on logging/__init__.py:findCaller and modified so it takes into account
    this file - https://hg.python.org/cpython/file/2.7/Lib/logging/__init__.py#l1233
    """
    rv = '(unknown file)', 0, '(unknown function)'

    try:
        f = logging.currentframe().f_back
        while hasattr(f, 'f_code'):
            co = f.f_code
            filename = os.path.normcase(co.co_filename)
            if filename in (_srcfile, logging._srcfile):  # This line is modified.
                f = f.f_back
                continue
            rv = (filename, f.f_lineno, co.co_name)
            break
    except Exception:
        pass

    return rv


def decorate_log_method(func):
    @wraps(func)
    def func_wrapper(*args, **kwargs):
        # Prefix extra keys with underscore
        if 'extra' in kwargs:
            kwargs['extra'] = prefix_dict_keys(dictionary=kwargs['extra'], prefix='_')

        try:
            return func(*args, **kwargs)
        except TypeError as e:
            # In some version of Python 2.7, logger.exception doesn't take any kwargs so we need
            # this hack :/
            # See:
            # - https://docs.python.org/release/2.7.3/library/logging.html#logging.Logger.exception
            # - https://docs.python.org/release/2.7.7/library/logging.html#logging.Logger.exception
            if 'got an unexpected keyword argument \'extra\'' in str(e):
                kwargs.pop('extra', None)
                return func(*args, **kwargs)
            raise e
    return func_wrapper


def decorate_logger_methods(logger):
    """
    Decorate all the logger methods so all the keys in the extra dictionary are
    automatically prefixed with an underscore to avoid clashes with standard log
    record attributes.
    """

    # Note: We override findCaller with our custom implementation which takes into account this
    # module.
    # This way filename, module, funcName and lineno LogRecord attributes contain correct values
    # instead of all pointing to decorate_log_method.
    logger.findCaller = find_caller
    for key in LOGGER_KEYS:
        log_method = getattr(logger, key)
        log_method = decorate_log_method(log_method)
        setattr(logger, key, log_method)

    return logger


def getLogger(name):
    # make sure that prefix isn't appended multiple times to preserve logging name hierarchy
    prefix = 'st2.'
    if name.startswith(prefix):
        logger = logging.getLogger(name)
    else:
        logger_name = '{}{}'.format(prefix, name)
        logger = logging.getLogger(logger_name)

    logger = decorate_logger_methods(logger=logger)
    return logger


class LoggingStream(object):

    def __init__(self, name, level=logging.ERROR):
        self._logger = getLogger(name)
        self._level = level

    def write(self, message):
        self._logger._log(self._level, message, None)

    def flush(self):
        pass


def _audit(logger, msg, *args, **kwargs):
    if logger.isEnabledFor(logging.AUDIT):
        logger._log(logging.AUDIT, msg, args, **kwargs)

logging.Logger.audit = _audit


def _add_exclusion_filters(handlers, excludes=None):
    if excludes:
        for h in handlers:
            h.addFilter(ExclusionFilter(excludes))


def _redirect_stderr():
    # It is ok to redirect stderr as none of the st2 handlers write to stderr.
    sys.stderr = LoggingStream('STDERR')


def setup(config_file, redirect_stderr=True, excludes=None, disable_existing_loggers=False):
    """
    Configure logging from file.
    """
    try:
        logging.config.fileConfig(config_file,
                                  defaults=None,
                                  disable_existing_loggers=disable_existing_loggers)
        handlers = logging.getLoggerClass().manager.root.handlers
        _add_exclusion_filters(handlers)
        if redirect_stderr:
            _redirect_stderr()
    except Exception as exc:
        # revert stderr redirection since there is no logger in place.
        sys.stderr = sys.__stderr__
        # No logger yet therefore write to stderr
        sys.stderr.write('ERROR: %s' % traceback.format_exc())
        raise Exception(six.text_type(exc))
