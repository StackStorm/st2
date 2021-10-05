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

import io
import os
import sys
import logging
import logging.config
import logging.handlers
import traceback
from functools import wraps

import six

from st2common.logging.filters import LoggerNameExclusionFilter

# Those are here for backward compatibility reasons
from st2common.logging.handlers import FormatNamedFileHandler
from st2common.logging.handlers import ConfigurableSyslogHandler
from st2common.util.misc import prefix_dict_keys
from st2common.util.misc import get_normalized_file_path

__all__ = [
    "getLogger",
    "setup",
    "FormatNamedFileHandler",
    "ConfigurableSyslogHandler",
    "LoggingStream",
    "ignore_lib2to3_log_messages",
    "ignore_statsd_log_messages",
]

# NOTE: We set AUDIT to the highest log level which means AUDIT log messages will always be
# included (e.g. also if log level is set to INFO). To avoid that, we need to explicitly filter
# out AUDIT log level in service setup code.
logging.AUDIT = logging.CRITICAL + 10
logging.addLevelName(logging.AUDIT, "AUDIT")

LOGGER_KEYS = [
    "debug",
    "info",
    "warning",
    "error",
    "critical",
    "exception",
    "log",
    "audit",
]

# True if sys.stdout should be patched and re-opened with utf-8 encoding in situations where
# utf-8 encoding is not used (if we don't do that and a logger tries to log a unicode string,
# log format would go in an infinite loop).
# We only expose this variable for testing purposes
PATCH_STDOUT = os.environ.get("ST2_LOG_PATCH_STDOUT", "true").lower() in [
    "true",
    "1",
    "yes",
]

LOG = logging.getLogger(__name__)

# Note: This attribute is used by "find_caller" so it can correctly exclude this file when looking
# for the logger method caller frame.
_srcfile = get_normalized_file_path(__file__)

_original_stdstderr = sys.stderr


def find_caller(stack_info=False, stacklevel=1):
    """
    Find the stack frame of the caller so that we can note the source file name, line number and
    function name.

    Note: This is based on logging/__init__.py:findCaller and modified so it takes into account
    this file:
    https://github.com/python/cpython/blob/2.7/Lib/logging/__init__.py#L1240-L1259

    The Python 3.x implementation adds in a new argument `stack_info` and `stacklevel`
    and expects a 4-element tuple to be returned, rather than a 3-element tuple in
    the python 2 implementation.
    We derived our implementation from the Python 3.9 source code here:
    https://github.com/python/cpython/blob/3.9/Lib/logging/__init__.py#L1502-L1536

    We've made the appropriate changes so that we're python 2 and python 3 compatible depending
    on what runtine we're working in.
    """
    if six.PY2:
        rv = "(unknown file)", 0, "(unknown function)"
    else:
        # python 3, has extra tuple element at the end for stack information
        rv = "(unknown file)", 0, "(unknown function)", None

    try:
        f = logging.currentframe()
        # On some versions of IronPython, currentframe() returns None if
        # IronPython isn't run with -X:Frames.
        if f is not None:
            f = f.f_back
        orig_f = f
        while f and stacklevel > 1:
            f = f.f_back
            stacklevel -= 1
        if not f:
            f = orig_f

        while hasattr(f, "f_code"):
            co = f.f_code
            filename = os.path.normcase(co.co_filename)
            if filename in (_srcfile, logging._srcfile):  # This line is modified.
                f = f.f_back
                continue

            if six.PY2:
                rv = (filename, f.f_lineno, co.co_name)
            else:
                # python 3, new stack_info processing and extra tuple return value
                sinfo = None
                if stack_info:
                    sio = io.StringIO()
                    sio.write("Stack (most recent call last):\n")
                    traceback.print_stack(f, file=sio)
                    sinfo = sio.getvalue()
                    if sinfo[-1] == "\n":
                        sinfo = sinfo[:-1]
                    sio.close()
                rv = (filename, f.f_lineno, co.co_name, sinfo)
            break
    except Exception as e:
        print(f"Unable to find caller. {e}")

    return rv


def decorate_log_method(func):
    @wraps(func)
    def func_wrapper(*args, **kwargs):
        # Prefix extra keys with underscore
        if "extra" in kwargs:
            kwargs["extra"] = prefix_dict_keys(dictionary=kwargs["extra"], prefix="_")

        try:
            return func(*args, **kwargs)
        except TypeError as e:
            # In some version of Python 2.7, logger.exception doesn't take any kwargs so we need
            # this hack :/
            # See:
            # - https://docs.python.org/release/2.7.3/library/logging.html#logging.Logger.exception
            # - https://docs.python.org/release/2.7.7/library/logging.html#logging.Logger.exception
            if "got an unexpected keyword argument 'extra'" in six.text_type(e):
                kwargs.pop("extra", None)
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
    prefix = "st2."
    if name.startswith(prefix):
        logger = logging.getLogger(name)
    else:
        logger_name = "{}{}".format(prefix, name)
        logger = logging.getLogger(logger_name)

    logger = decorate_logger_methods(logger=logger)
    return logger


class LoggingStream(object):
    def __init__(self, name, level=logging.ERROR):
        self._logger = getLogger(name)
        self._level = level

    def write(self, message):
        # Work around for infinite loop issue - ensure we don't log unicode data.
        # If message contains unicode sequences and process locale is not set to utf-8, it would
        # result in infinite lop in _log on formatting the message.
        # This is because of the differences between Python 2.7 and Python 3 with log error
        # handlers.
        message = message.encode("utf-8", "replace").decode("ascii", "ignore")

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
            h.addFilter(LoggerNameExclusionFilter(excludes))


def _redirect_stderr():
    # It is ok to redirect stderr as none of the st2 handlers write to stderr.
    sys.stderr = LoggingStream("STDERR")


def _patch_stdout():
    """
    This function re-opens sys.stdout using utf-8 encoding.

    It's to be used in situations where process encoding / locale is not set to utf-8. In such
    situations when unicode sequence is logged, it would cause logging formatter to go in an infite
    loop on formatting a record.

    This function works around that by ensuring sys.stdout is always opened in utf-8 mode.
    """

    stdout_encoding = str(getattr(sys.stdout, "encoding", "none")).lower()

    if stdout_encoding not in ["utf8", "utf-8"] and PATCH_STDOUT:
        LOG.info(
            "Patching sys.stdout and re-opening it with utf-8 encoding (originally opened "
            "with %s encoding)..." % (stdout_encoding)
        )
        sys.stdout = open(
            sys.stdout.fileno(),
            mode="w",
            encoding="utf-8",
            errors="replace",
            buffering=1,
        )


def setup(
    config_file,
    redirect_stderr=True,
    excludes=None,
    disable_existing_loggers=False,
    st2_conf_path=None,
):
    """
    Configure logging from file.

    :param st2_conf_path: Optional path to st2.conf file. If provided and "config_file" path is
                          relative to st2.conf path, the config_file path will get resolved to full
                          absolute path relative to st2.conf.
    :type st2_conf_path: ``str``
    """
    if st2_conf_path and config_file[:2] == "./" and not os.path.isfile(config_file):
        # Logging config path is relative to st2.conf, resolve it to full absolute path
        directory = os.path.dirname(st2_conf_path)
        config_file_name = os.path.basename(config_file)
        config_file = os.path.join(directory, config_file_name)

    try:
        logging.config.fileConfig(
            config_file,
            defaults=None,
            disable_existing_loggers=disable_existing_loggers,
        )
        handlers = logging.getLoggerClass().manager.root.handlers
        _add_exclusion_filters(handlers=handlers, excludes=excludes)
        if redirect_stderr:
            _redirect_stderr()
        _patch_stdout()
    except Exception as exc:
        exc_cls = type(exc)
        tb_msg = traceback.format_exc()

        msg = str(exc)
        msg += "\n\n" + tb_msg

        # revert stderr redirection since there is no logger in place.
        sys.stderr = sys.__stderr__

        # No logger yet therefore write to stderr
        sys.stderr.write("ERROR: %s" % (msg))

        raise exc_cls(six.text_type(msg))


def ignore_lib2to3_log_messages():
    """
    Work around to ignore "Generating grammar tables from" log messages which are logged under
    INFO by default by libraries such as networkx which use 2to3.
    """
    import lib2to3.pgen2.driver

    class MockLoggingModule(object):
        def getLogger(self, *args, **kwargs):
            return logging.getLogger("lib2to3")

    lib2to3.pgen2.driver.logging = MockLoggingModule()
    logging.getLogger("lib2to3").setLevel(logging.ERROR)


def ignore_statsd_log_messages():
    """
    By default statsd client logs all the operations under INFO and that causes a lot of noise.

    This pull request silences all the statsd INFO log messages.
    """
    import statsd.connection
    import statsd.client

    class MockLoggingModule(object):
        def getLogger(self, *args, **kwargs):
            return logging.getLogger("statsd")

    statsd.connection.logging = MockLoggingModule()
    statsd.client.logging = MockLoggingModule()
    logging.getLogger("statsd").setLevel(logging.ERROR)
