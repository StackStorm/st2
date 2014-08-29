import datetime
import logging
import logging.config
import six
from six import moves

logging.AUDIT = logging.CRITICAL + 10
logging.addLevelName(logging.AUDIT, 'AUDIT')


class TimeStampedFileHandler(logging.FileHandler):
    def __init__(self, filename, mode='a', encoding=None, delay=False):
        # Include timestamp in the name.
        filename = filename.format(str(datetime.datetime.now()).replace(' ', '_'))
        super(TimeStampedFileHandler, self).__init__(filename, mode, encoding, delay)


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
        import sys
        import traceback
        sys.stderr.write('ERROR: %s' % traceback.format_exc())
        raise Exception(six.text_type(exc))


def getLogger(name):
    return logging.getLogger(name)
