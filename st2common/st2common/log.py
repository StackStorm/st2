import datetime
import logging
import logging.config
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


class ConfigurableSyslogHandler(logging.SysLogHandler):
    def __init__(self, address=None, facility=None, socktype=None):
        if not address:
            address = (cfg.CONF.syslog.host, cfg.CONF.syslog.port)
        if not facility:
            facility = cfg.CONF.syslog.facility
        if socktype:
            super(ConfigurableSyslogHandler, self).__init__(address, facility, socktype)
        else:
            super(ConfigurableSyslogHandler, self).__init__(address, facility)


def _audit(logger, msg, *args, **kwargs):
    if logger.isEnabledFor(logging.AUDIT):
        logger._log(logging.AUDIT, msg, args, **kwargs)

logging.Logger.audit = _audit


def setup(config_file):
    """Configure logging from file.
    """
    try:
        logging.config.fileConfig(config_file,
                                  defaults=None,
                                  disable_existing_loggers=False)
    except Exception as exc:
        # No logger yet therefore write to stderr
        sys.stderr.write('ERROR: %s' % traceback.format_exc())
        raise Exception(six.text_type(exc))


def getLogger(name):
    return logging.getLogger(name)
