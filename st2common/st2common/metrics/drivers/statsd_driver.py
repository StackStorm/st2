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

from numbers import Number

import statsd
from oslo_config import cfg

from st2common.metrics.base import BaseMetricsDriver
from st2common.metrics.utils import check_key
from st2common.metrics.utils import get_full_key_name

__all__ = [
    'StatsdDriver'
]


class StatsdDriver(BaseMetricsDriver):
    """
    StatsD Implementation of the metrics driver
    """
    def __init__(self):
        statsd.Connection.set_defaults(host=cfg.CONF.metrics.host, port=cfg.CONF.metrics.port,
                                       sample_rate=cfg.CONF.metrics.sample_rate)

    def time(self, key, time):
        """
        Timer metric
        """
        check_key(key)
        assert isinstance(time, Number)

        key = get_full_key_name(key)
        timer = statsd.Timer('')
        timer.send(key, time)

    def inc_counter(self, key, amount=1):
        """
        Increment counter
        """
        check_key(key)
        assert isinstance(amount, Number)

        key = get_full_key_name(key)
        counter = statsd.Counter(key)
        counter.increment(delta=amount)

    def dec_counter(self, key, amount=1):
        """
        Decrement metric
        """
        check_key(key)
        assert isinstance(amount, Number)

        key = get_full_key_name(key)
        counter = statsd.Counter(key)
        counter.decrement(delta=amount)

    def set_gauge(self, key, value):
        """
        Set gauge value.
        """
        check_key(key)
        assert isinstance(value, Number)

        key = get_full_key_name(key)
        gauge = statsd.Gauge(key)
        gauge.send(None, value)

    def inc_gauge(self, key, amount=1):
        """
        Increment gauge value.
        """
        check_key(key)
        assert isinstance(amount, Number)

        key = get_full_key_name(key)
        gauge = statsd.Gauge(key)
        gauge.increment(None, amount)

    def dec_gauge(self, key, amount=1):
        """
        Decrement gauge value.
        """
        check_key(key)
        assert isinstance(amount, Number)

        key = get_full_key_name(key)
        gauge = statsd.Gauge(key)
        gauge.decrement(None, amount)
