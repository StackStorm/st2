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
from __future__ import absolute_import
from datetime import datetime
from functools import wraps

from oslo_config import cfg

from st2common.constants.metrics import METRICS_COUNTER_SUFFIX, METRICS_TIMER_SUFFIX


BACKENDS_NAMESPACE = 'st2common.metrics.driver'


def get_available_drivers():
    """
    Return names of the available / installed action runners.

    :rtype: ``list`` of ``str``
    """
    from stevedore.extension import ExtensionManager

    manager = ExtensionManager(namespace=BACKENDS_NAMESPACE, invoke_on_load=False)
    return manager.names()


def get_driver_instance(name):
    """
    Return a class instance for the provided runner name.
    """
    from stevedore.driver import DriverManager

    manager = DriverManager(namespace=BACKENDS_NAMESPACE, name=name, invoke_on_load=False)
    return manager.driver


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

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kw):
            with self as metrics_timer:
                return func(*args, metrics_timer=metrics_timer, **kw)
        return wrapper


class Counter(object):
    """ Timer context manager for easily sending timer statistics.
    """
    def __init__(self, key):
        assert isinstance(key, str)
        assert key
        self.key = key
        self._metrics = METRICS

    def __enter__(self):
        self._metrics.inc_counter(self.key)
        return self

    def __exit__(self, *args):
        self._metrics.dec_counter(self.key)

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kw):
            with self:
                return func(*args, **kw)
        return wrapper


class CounterWithTimer(object):
    """ Timer and counter context manager for easily sending timer statistics
    with builtin timer.
    """
    def __init__(self, key):
        assert isinstance(key, str)
        assert key
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

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kw):
            with self as counter_with_timer:
                return func(*args, metrics_counter_with_timer=counter_with_timer, **kw)
        return wrapper
