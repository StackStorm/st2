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

import socket
import logging as stdlib_logging
from numbers import Number

import statsd
from oslo_config import cfg

from st2common import log as logging
from st2common.metrics.base import BaseMetricsDriver
from st2common.metrics.utils import check_key
from st2common.metrics.utils import get_full_key_name
from st2common.util.misc import ignore_and_log_exception


LOG = logging.getLogger(__name__)

# Which exceptions thrown by statsd library should be considered as non-fatal
NON_FATAL_EXC_CLASSES = [socket.error, IOError, OSError]

__all__ = ["StatsdDriver"]


class StatsdDriver(BaseMetricsDriver):
    """
    StatsD Implementation of the metrics driver

    NOTE: Statsd uses UDP which is "fire and forget" and any kind of send error is not fatal. There
    is an issue with python-statsd library though which doesn't ignore DNS resolution related errors
    and bubbles them all the way up.

    This of course breaks the application. Any kind of metric related errors should be considered
    as non-fatal and not degrade application in any way if an error occurs. That's why we wrap all
    the statsd library calls here to ignore the errors and just log them.
    """

    def __init__(self):
        statsd.Connection.set_defaults(
            host=cfg.CONF.metrics.host,
            port=cfg.CONF.metrics.port,
            sample_rate=cfg.CONF.metrics.sample_rate,
        )

    @ignore_and_log_exception(
        exc_classes=NON_FATAL_EXC_CLASSES, logger=LOG, level=stdlib_logging.WARNING
    )
    def time(self, key, time):
        """
        Timer metric
        """
        check_key(key)
        assert isinstance(time, Number)

        key = get_full_key_name(key)
        timer = statsd.Timer("")
        timer.send(key, time)

    @ignore_and_log_exception(
        exc_classes=NON_FATAL_EXC_CLASSES, logger=LOG, level=stdlib_logging.WARNING
    )
    def inc_counter(self, key, amount=1):
        """
        Increment counter
        """
        check_key(key)
        assert isinstance(amount, Number)

        key = get_full_key_name(key)
        counter = statsd.Counter(key)
        counter.increment(delta=amount)

    @ignore_and_log_exception(
        exc_classes=NON_FATAL_EXC_CLASSES, logger=LOG, level=stdlib_logging.WARNING
    )
    def dec_counter(self, key, amount=1):
        """
        Decrement metric
        """
        check_key(key)
        assert isinstance(amount, Number)

        key = get_full_key_name(key)
        counter = statsd.Counter(key)
        counter.decrement(delta=amount)

    @ignore_and_log_exception(
        exc_classes=NON_FATAL_EXC_CLASSES, logger=LOG, level=stdlib_logging.WARNING
    )
    def set_gauge(self, key, value):
        """
        Set gauge value.
        """
        check_key(key)
        assert isinstance(value, Number)

        key = get_full_key_name(key)
        gauge = statsd.Gauge(key)
        gauge.send(None, value)

    @ignore_and_log_exception(
        exc_classes=NON_FATAL_EXC_CLASSES, logger=LOG, level=stdlib_logging.WARNING
    )
    def inc_gauge(self, key, amount=1):
        """
        Increment gauge value.
        """
        check_key(key)
        assert isinstance(amount, Number)

        key = get_full_key_name(key)
        gauge = statsd.Gauge(key)
        gauge.increment(None, amount)

    @ignore_and_log_exception(
        exc_classes=NON_FATAL_EXC_CLASSES, logger=LOG, level=stdlib_logging.WARNING
    )
    def dec_gauge(self, key, amount=1):
        """
        Decrement gauge value.
        """
        check_key(key)
        assert isinstance(amount, Number)

        key = get_full_key_name(key)
        gauge = statsd.Gauge(key)
        gauge.decrement(None, amount)
