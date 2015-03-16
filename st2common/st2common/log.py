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
import logging.config
import logging.handlers
import sys
import traceback

import six
from oslo.config import cfg

from st2common.logging.filters import ExclusionFilter

# Those are here for backward compatibility reasons
from st2common.logging.handlers import FormatNamedFileHandler
from st2common.logging.handlers import ConfigurableSyslogHandler

__all__ = [
    'getLogger',
    'setup',

    'FormatNamedFileHandler',
    'ConfigurableSyslogHandler',

    'LoggingStream'
]

logging.AUDIT = logging.CRITICAL + 10
logging.addLevelName(logging.AUDIT, 'AUDIT')


def getLogger(name):
    logger_name = 'st2.{}'.format(name)
    return logging.getLogger(logger_name)


class LoggingStream(object):

    def __init__(self, name, level=logging.ERROR):
        self._logger = getLogger(name)
        self._level = level

    def write(self, message):
        self._logger._log(self._level, message, None)


def _audit(logger, msg, *args, **kwargs):
    if logger.isEnabledFor(logging.AUDIT):
        logger._log(logging.AUDIT, msg, args, **kwargs)

logging.Logger.audit = _audit


def _add_exclusion_filters(handlers):
    for h in handlers:
        h.addFilter(ExclusionFilter(cfg.CONF.log.excludes))


def _redirect_stderr():
    # It is ok to redirect stderr as none of the st2 handlers write to stderr.
    if cfg.CONF.log.redirect_stderr:
        sys.stderr = LoggingStream('STDERR')


def setup(config_file, disable_existing_loggers=False):
    """
    Configure logging from file.
    """
    try:
        logging.config.fileConfig(config_file,
                                  defaults=None,
                                  disable_existing_loggers=disable_existing_loggers)
        handlers = logging.getLoggerClass().manager.root.handlers
        _add_exclusion_filters(handlers)
        _redirect_stderr()
    except Exception as exc:
        # revert stderr redirection since there is no logger in place.
        sys.stderr = sys.__stderr__
        # No logger yet therefore write to stderr
        sys.stderr.write('ERROR: %s' % traceback.format_exc())
        raise Exception(six.text_type(exc))
