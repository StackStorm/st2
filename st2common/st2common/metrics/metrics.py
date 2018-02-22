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
from datetime import datetime

from oslo_config import cfg

from st2common.constants.metrics import METRICS_COUNTER_SUFFIX, METRICS_TIMER_SUFFIX


class BaseMetricsDriver(object):
    """ Base class for driver implementations for metric collection
    """
    def time(self, key, time):
        """ Timer metric
        """
        pass

    def inc_counter(self, key, amount=1):
        """ Increment counter
        """
        pass

    def dec_counter(self, key, amount=1):
        """ Decrement metric
        """
        pass


class Timer(object):
    """ Timer context manager for easily sending timer statistics.
    """
    def __init__(self, key):
        assert isinstance(key, str)
        assert len(key) > 0
        self.key = key
        self._metrics = METRICS
        self._start_time = None

    def send_time(self, key=None):
        """ Send current time from start time.
        """
        time_delta = datetime.now() - self._start_time

        if key:
            assert isinstance(key, str)
            self._metrics.time(key, time_delta.total_seconds())
        else:
            self._metrics.time(self.key, time_delta.total_seconds())

    def get_time_delta(self):
        """ Get current time delta.
        """
        return datetime.now() - self._start_time

    def __enter__(self):
        self._start_time = datetime.now()
        return self

    def __exit__(self, *args):
        self.send_time()


class Counter(object):
    """ Timer context manager for easily sending timer statistics.
    """
    def __init__(self, key):
        assert isinstance(key, str)
        assert len(key) > 0
        self.key = key
        self._metrics = METRICS

    def __enter__(self):
        self._metrics.inc_counter(self.key)
        return self

    def __exit__(self, *args):
        self._metrics.dec_counter(self.key)


class CounterWithTimer(object):
    """ Timer and counter context manager for easily sending timer statistics
    with builtin timer.
    """
    def __init__(self, key):
        assert isinstance(key, str)
        assert len(key) > 0
        self.key = key
        self._metrics = METRICS
        self._start_time = None

    def send_time(self, key=None):
        """ Send current time from start time.
        """
        time_delta = datetime.now() - self._start_time

        if key:
            assert isinstance(key, str)
            self._metrics.time(key, time_delta.total_seconds())
        else:
            self._metrics.time("%s%s" % (self.key, METRICS_TIMER_SUFFIX),
                               time_delta.total_seconds())

    def get_time_delta(self):
        """ Get current time delta.
        """
        return datetime.now() - self._start_time

    def __enter__(self):
        self._metrics.inc_counter("%s%s" % (self.key, METRICS_COUNTER_SUFFIX))
        self._start_time = datetime.now()
        return self

    def __exit__(self, *args):
        self.send_time()
        self._metrics.dec_counter("%s_counter" % self.key)


def _get_metrics_driver():
    driver = cfg.CONF.metrics.driver

    if driver == "prometheus" and cfg.CONF.metrics.enable:
        from st2common.metrics.drivers.prometheus import PrometheusDriver
        return PrometheusDriver()
    elif driver == "statsd" and cfg.CONF.metrics.enable:
        from st2common.metrics.drivers.statsd_driver import StatsdDriver
        return StatsdDriver()

    return BaseMetricsDriver()


METRICS = _get_metrics_driver()
