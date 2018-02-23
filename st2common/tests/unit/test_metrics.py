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

import unittest2
from mock import patch, MagicMock

from st2common import config as st2common_config
st2common_config.parse_args(args=[])
from oslo_config import cfg

from st2common.metrics import metrics
from st2common.metrics.drivers.statsd_driver import StatsdDriver

__all__ = [
    'TestBaseMetricsDriver'
]


class TestBaseMetricsDriver(unittest2.TestCase):
    _driver = None

    def setUp(self):
        self._driver = metrics.BaseMetricsDriver()

    def test_time(self):
        self._driver.time('test', 10)

    def test_inc_counter(self):
        self._driver.inc_counter('test')

    def test_dec_timer(self):
        self._driver.dec_counter('test')


class TestStatsDMetricsDriver(unittest2.TestCase):
    _driver = None

    @patch('st2common.metrics.drivers.statsd_driver.statsd')
    def setUp(self, statsd):
        self._driver = StatsdDriver()
        self._driver._connection = MagicMock()

        statsd.StatsClient.assert_called_once_with(cfg.CONF.metrics.host, cfg.CONF.metrics.port)

    def test_time(self):
        params = ('test', 10)
        self._driver.time(*params)
        self._driver._connection.timing.assert_called_with(*params)

    def test_time_with_float(self):
        params = ('test', 10.5)
        self._driver.time(*params)
        self._driver._connection.timing.assert_called_with(*params)

    def test_time_with_invalid_key(self):
        params = (2, 2)
        with self.assertRaises(AssertionError):
            self._driver.time(*params)

    def test_time_with_invalid_time(self):
        params = ('test', '1')
        with self.assertRaises(AssertionError):
            self._driver.time(*params)

    def test_inc_counter_with_default_amount(self):
        key = 'test'
        self._driver.inc_counter(key)
        self._driver._connection.incr.assert_called_with(key, 1)

    def test_inc_counter_with_amount(self):
        params = ('test', 2)
        self._driver.inc_counter(*params)
        self._driver._connection.incr.assert_called_with(*params)

    def test_inc_timer_with_invalid_key(self):
        params = (2, 2)
        with self.assertRaises(AssertionError):
            self._driver.inc_counter(*params)

    def test_inc_timer_with_invalid_amount(self):
        params = ('test', '1')
        with self.assertRaises(AssertionError):
            self._driver.inc_counter(*params)

    def test_dec_timer_with_default_amount(self):
        key = 'test'
        self._driver.dec_counter(key)
        self._driver._connection.decr.assert_called_with(key, 1)

    def test_dec_timer_with_amount(self):
        params = ('test', 2)
        self._driver.dec_counter(*params)
        self._driver._connection.decr.assert_called_with(*params)

    def test_dec_timer_with_invalid_key(self):
        params = (2, 2)
        with self.assertRaises(AssertionError):
            self._driver.dec_counter(*params)

    def test_dec_timer_with_invalid_amount(self):
        params = ('test', '1')
        with self.assertRaises(AssertionError):
            self._driver.dec_counter(*params)


class TestCounterContextManager(unittest2.TestCase):
    _base_metrics_driver = None

    def setUp(self):
        self._base_metrics_driver = metrics.BaseMetricsDriver()

    def test_time(self):
        self._base_metrics_driver.time('test', 10)

    def test_inc_counter(self):
        self._base_metrics_driver.inc_counter('test')

    def test_dec_timer(self):
        self._base_metrics_driver.dec_counter('test')
