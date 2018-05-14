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
from oslo_config import cfg
import statsd

from st2common.metrics.base import BaseMetricsDriver


class StatsdDriver(BaseMetricsDriver):
    """ StatsD Implementation of the metrics driver
    """
    def __init__(self):
        statsd.Connection.set_defaults(host=cfg.CONF.metrics.host, port=cfg.CONF.metrics.port)
        self._counters = {}
        self._timers = {}

    def time(self, key, time):
        """ Timer metric
        """
        assert isinstance(key, str)
        assert isinstance(time, Number)
        self._timers[key] = self._timers.get(key, statsd.Timer(''))
        self._timers[key].send(key, time)

    def inc_counter(self, key, amount=1):
        """ Increment counter
        """
        assert isinstance(key, str)
        assert isinstance(amount, Number)
        self._counters[key] = self._counters.get(key, statsd.Counter(key))
        self._counters[key] += amount

    def dec_counter(self, key, amount=1):
        """ Decrement metric
        """
        assert isinstance(key, str)
        assert isinstance(amount, Number)
        self._counters[key] = self._counters.get(key, statsd.Counter(key))
        self._counters[key] -= amount
