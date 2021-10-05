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
import os
import socket
import time
import logging

from oslo_config import cfg

from st2common.util import date as date_utils

__all__ = [
    "FormatNamedFileHandler",
    "ConfigurableSyslogHandler",
]


class FormatNamedFileHandler(logging.handlers.RotatingFileHandler):
    def __init__(
        self, filename, mode="a", maxBytes=0, backupCount=0, encoding=None, delay=False
    ):
        # We add aditional values to the context which can be used in the log filename
        timestamp = int(time.time())
        isotime_str = str(date_utils.get_datetime_utc_now()).replace(" ", "_")
        pid = os.getpid()
        format_values = {"timestamp": timestamp, "ts": isotime_str, "pid": pid}
        filename = filename.format(**format_values)
        super(FormatNamedFileHandler, self).__init__(
            filename,
            mode=mode,
            maxBytes=maxBytes,
            backupCount=backupCount,
            encoding=encoding,
            delay=delay,
        )


class ConfigurableSyslogHandler(logging.handlers.SysLogHandler):
    def __init__(self, address=None, facility=None, socktype=None):
        if not address:
            address = (cfg.CONF.syslog.host, cfg.CONF.syslog.port)
        if not facility:
            facility = cfg.CONF.syslog.facility
        if not socktype:
            protocol = cfg.CONF.syslog.protocol.lower()

            if protocol == "udp":
                socktype = socket.SOCK_DGRAM
            elif protocol == "tcp":
                socktype = socket.SOCK_STREAM
            else:
                raise ValueError("Unsupported protocol: %s" % (protocol))

        if socktype:
            super(ConfigurableSyslogHandler, self).__init__(address, facility, socktype)
        else:
            super(ConfigurableSyslogHandler, self).__init__(address, facility)
