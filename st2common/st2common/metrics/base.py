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
from functools import wraps
import logging
from six import string_types

from oslo_config import cfg
from oslo_config.cfg import NoSuchOptError
from stevedore.exception import NoMatches, MultipleMatches

from st2common.constants.metrics import METRICS_COUNTER_SUFFIX, METRICS_TIMER_SUFFIX
from st2common.util.loader import get_plugin_instance
from st2common.util.date import get_datetime_utc_now
from st2common.exceptions.plugins import PluginLoadError


LOG = logging.getLogger(__name__)

PLUGIN_NAMESPACE = 'st2common.metrics.driver'
METRICS = None


def format_metrics_key(action_db=None, liveaction_db=None, key=None):
    """Return a string for usage as metrics key.
    """
    assert (action_db or key or liveaction_db), """Must supply one of key, action_db, or
                                                 liveaction_db"""
    suffix = ""

    if action_db:
        action_name = action_db.name
        action_pack = action_db.pack

        suffix = "%s.%s" % (action_pack, action_name)
    elif liveaction_db:
        action_name = liveaction_db.action
        action_pack = liveaction_db.context.get('pack', 'nopack')

        suffix = "%s.%s" % (action_pack, action_name)

    if key and not suffix:
        suffix = key
    elif key and suffix:
        suffix = "%s.%s" % (suffix, key)

    metrics_key = "st2.%s" % (suffix)

    LOG.debug("Generated Metrics Key: %s", metrics_key)

    return metrics_key


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


def check_key(key):
    """Ensure key meets requirements.
    """
    assert isinstance(key, string_types), "Key not a string. Got %s" % type(key)
    assert key, "Key cannot be empty string."


class Timer(object):
    """ Timer context manager for easily sending timer statistics.
    """
    def __init__(self, key):
        check_key(key)
        self.key = key
        self._metrics = get_driver()
        self._start_time = None

    def send_time(self, key=None):
        """ Send current time from start time.
        """
        time_delta = get_datetime_utc_now() - self._start_time

        if key:
            check_key(key)
            self._metrics.time(key, time_delta.total_seconds())
        else:
            self._metrics.time(self.key, time_delta.total_seconds())

    def get_time_delta(self):
        """ Get current time delta.
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
                return func(*args, metrics_timer=metrics_timer, **kw)
        return wrapper


class Counter(object):
    """ Timer context manager for easily sending timer statistics.
    """
    def __init__(self, key):
        check_key(key)
        self.key = key
        self._metrics = get_driver()

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
        check_key(key)
        self.key = key
        self._metrics = get_driver()
        self._start_time = None

    def send_time(self, key=None):
        """ Send current time from start time.
        """
        time_delta = get_datetime_utc_now() - self._start_time

        if key:
            check_key(key)
            self._metrics.time(key, time_delta.total_seconds())
        else:
            self._metrics.time("%s%s" % (self.key, METRICS_TIMER_SUFFIX),
                               time_delta.total_seconds())

    def get_time_delta(self):
        """ Get current time delta.
        """
        return get_datetime_utc_now() - self._start_time

    def __enter__(self):
        self._metrics.inc_counter("%s%s" % (self.key, METRICS_COUNTER_SUFFIX))
        self._start_time = get_datetime_utc_now()
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


def metrics_initialize():
    """Initialize metrics constant
    """
    global METRICS
    try:
        METRICS = get_plugin_instance(PLUGIN_NAMESPACE, cfg.CONF.metrics.driver)
    except (NoMatches, MultipleMatches, NoSuchOptError) as error:
        raise PluginLoadError('Error loading metrics driver. Check configuration: %s', error)

    return METRICS


def get_driver():
    """Return metrics driver instance
    """
    if not METRICS:
        return metrics_initialize()

    return METRICS
