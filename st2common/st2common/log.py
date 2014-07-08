
import logging
import logging.config
import six
from six import moves


logging.AUDIT = logging.CRITICAL + 10
logging.addLevelName(logging.AUDIT, 'AUDIT')


_loggers = {}


def setup(config_file):
    """Configure logging from file.
    """
    try:
        logging.config.fileConfig(config_file,
                                  defaults=None,
                                  disable_existing_loggers=False)
    except moves.configparser.Error as exc:
        raise Exception(six.text_type(exc))


def getLogger(name, extra=None):
    if name not in _loggers:
        _loggers[name] = AuditLoggerAdapter(logging.getLogger(name), extra)
    return _loggers[name]


class AuditLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter to write message with the audit log level.
    """

    def audit(self, msg, *args, **kwargs):
        self.log(logging.AUDIT, msg, *args, **kwargs)

    def setLevel(self, lvl):
        self.logger.setLevel(lvl)

    def getEffectiveLevel(self):
        return self.logger.getEffectiveLevel()
