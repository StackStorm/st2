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

from functools import wraps
import logging

from oslo_config import cfg
from oslo_config.cfg import NoSuchOptError
from stevedore.exception import NoMatches, MultipleMatches

from st2common.metrics.utils import check_key
from st2common.util.loader import get_plugin_instance
from st2common.util.date import get_datetime_utc_now
from st2common.exceptions.plugins import PluginLoadError

__all__ = [
    "BaseMetricsDriver",
    "Timer",
    "Counter",
    "CounterWithTimer",
    "metrics_initialize",
    "get_driver",
]

if not hasattr(cfg.CONF, "metrics"):
    from st2common.config import register_opts

    register_opts()

LOG = logging.getLogger(__name__)

PLUGIN_NAMESPACE = "st2common.metrics.driver"  # pants: no-infer-dep

# Stores reference to the metrics driver class instance.
# NOTE: This value is populated lazily on the first get_driver() function call
METRICS = None


class BaseMetricsDriver(object):
    """
    Base class for driver implementations for metric collection
    """

    def time(self, key, time):
        """
        Timer metric
        """
        pass

    def inc_counter(self, key, amount=1):
        """
        Increment counter
        """
        pass

    def dec_counter(self, key, amount=1):
        """
        Decrement metric
        """
        pass

    def set_gauge(self, key, value):
        """
        Set gauge value.
        """
        pass

    def inc_gauge(self, key, amount=1):
        """
        Increment gauge value.
        """
        pass

    def dec_gauge(self, key, amount=1):
        """
        Decrement gauge value.
        """
        pass


class Timer(object):
    """
    Timer context manager for easily sending timer statistics.
    """

    def __init__(self, key, include_parameter=False):
        check_key(key)

        self.key = key
        self._metrics = get_driver()
        self._include_parameter = include_parameter
        self._start_time = None

    def send_time(self, key=None):
        """
        Send current time from start time.
        """
        time_delta = self.get_time_delta()

        if key:
            check_key(key)
            self._metrics.time(key, time_delta.total_seconds())
        else:
            self._metrics.time(self.key, time_delta.total_seconds())

    def get_time_delta(self):
        """
        Get current time delta.
        """

        return get_datetime_utc_now() - self._start_time

    def __enter__(self):
        self._start_time = get_datetime_utc_now()
        return self

    def __exit__(self, *args):
        self.send_time()

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kw):
            with self as metrics_timer:
                if self._include_parameter:
                    kw["metrics_timer"] = metrics_timer
                return func(*args, **kw)

        return wrapper


class Counter(object):
    """
    Counter context manager for easily sending counter statistics.
    """

    def __init__(self, key):
        check_key(key)
        self.key = key
        self._metrics = get_driver()

    def __enter__(self):
        self._metrics.inc_counter(self.key)
        return self

    def __exit__(self, *args):
        pass

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kw):
            with self:
                return func(*args, **kw)

        return wrapper


class CounterWithTimer(object):
    """
    Timer and counter context manager for easily sending counter statistics
    with builtin timer.
    """

    def __init__(self, key, include_parameter=False):
        check_key(key)
        self.key = key
        self._metrics = get_driver()
        self._include_parameter = include_parameter
        self._start_time = None

    def send_time(self, key=None):
        """
        Send current time from start time.
        """
        time_delta = self.get_time_delta()

        if key:
            check_key(key)
            self._metrics.time(key, time_delta.total_seconds())
        else:
            self._metrics.time(self.key, time_delta.total_seconds())

    def get_time_delta(self):
        """
        Get current time delta.
        """
        return get_datetime_utc_now() - self._start_time

    def __enter__(self):
        self._metrics.inc_counter(self.key)
        self._start_time = get_datetime_utc_now()
        return self

    def __exit__(self, *args):
        self.send_time()

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kw):
            with self as counter_with_timer:
                if self._include_parameter:
                    kw["metrics_counter_with_timer"] = counter_with_timer
                return func(*args, **kw)

        return wrapper


def metrics_initialize():
    """
    Initialize metrics constant
    """
    global METRICS

    try:
        METRICS = get_plugin_instance(PLUGIN_NAMESPACE, cfg.CONF.metrics.driver)
    except (NoMatches, MultipleMatches, NoSuchOptError) as error:
        raise PluginLoadError(
            "Error loading metrics driver. Check configuration: %s" % error
        )

    return METRICS


def get_driver():
    """
    Return metrics driver instance
    """
    if not METRICS:
        return metrics_initialize()

    return METRICS
