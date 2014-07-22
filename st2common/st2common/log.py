
import logging
import logging.config
import six
from six import moves


logging.AUDIT = logging.CRITICAL + 10
logging.addLevelName(logging.AUDIT, 'AUDIT')


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
    except moves.configparser.Error as exc:
        raise Exception(six.text_type(exc))


def getLogger(name):
    return logging.getLogger(name)
