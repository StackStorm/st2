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

import datetime
import logging
import logging.config
import logging.handlers
import os
import six
import sys
import traceback

from oslo.config import cfg

logging.AUDIT = logging.CRITICAL + 10
logging.addLevelName(logging.AUDIT, 'AUDIT')


class FormatNamedFileHandler(logging.FileHandler):
    def __init__(self, filename, mode='a', encoding=None, delay=False):
        # Include timestamp in the name.
        filename = filename.format(ts=str(datetime.datetime.utcnow()).replace(' ', '_'),
                                   pid=os.getpid())
        super(FormatNamedFileHandler, self).__init__(filename, mode, encoding, delay)


class ConfigurableSyslogHandler(logging.handlers.SysLogHandler):
    def __init__(self, address=None, facility=None, socktype=None):
        if not address:
            address = (cfg.CONF.syslog.host, cfg.CONF.syslog.port)
        if not facility:
            facility = cfg.CONF.syslog.facility
        if socktype:
            super(ConfigurableSyslogHandler, self).__init__(address, facility, socktype)
        else:
            super(ConfigurableSyslogHandler, self).__init__(address, facility)


class ExclusionFilter(object):

    def __init__(self, exclusions):
        self._exclusions = set(exclusions)

    def filter(self, record):
        if len(self._exclusions) < 1:
            return True
        module_decomposition = record.name.split('.')
        exclude = len(module_decomposition) > 0 and module_decomposition[0] in self._exclusions
        return not exclude


def _audit(logger, msg, *args, **kwargs):
    if logger.isEnabledFor(logging.AUDIT):
        logger._log(logging.AUDIT, msg, args, **kwargs)

logging.Logger.audit = _audit


def _add_exclusion_filters(handlers):
    for h in handlers:
            h.addFilter(ExclusionFilter(cfg.CONF.log.excludes))


def setup(config_file, disable_existing_loggers=False):
    """Configure logging from file.
    """
    try:
        logging.config.fileConfig(config_file,
                                  defaults=None,
                                  disable_existing_loggers=disable_existing_loggers)
        handlers = logging.getLoggerClass().manager.root.handlers
        _add_exclusion_filters(handlers)
    except Exception as exc:
        # No logger yet therefore write to stderr
        sys.stderr.write('ERROR: %s' % traceback.format_exc())
        raise Exception(six.text_type(exc))


def getLogger(name):
    logger_name = 'st2.{}'.format(name)
    return logging.getLogger(logger_name)
