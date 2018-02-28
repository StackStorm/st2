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
from datetime import datetime, timedelta

import unittest2
from mock import patch, MagicMock

from oslo_config import cfg

from st2common.metrics import metrics
from st2common.metrics.drivers.statsd_driver import StatsdDriver
from st2common.constants.metrics import METRICS_COUNTER_SUFFIX, METRICS_TIMER_SUFFIX

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
    @patch('st2common.metrics.metrics.METRICS')
    def test_counter(self, metrics_patch):
        test_key = "test_key"
        with metrics.Counter(test_key):
            metrics_patch.inc_counter.assert_called_with(test_key)
            metrics_patch.dec_counter.assert_not_called()
        metrics_patch.dec_counter.assert_called_with(test_key)


class TestTimerContextManager(unittest2.TestCase):
    @patch('st2common.metrics.metrics.datetime')
    @patch('st2common.metrics.metrics.METRICS')
    def test_time(self, metrics_patch, datetime_patch):
        start_time = datetime.now()
        middle_time = start_time + timedelta(seconds=1)
        end_time = middle_time + timedelta(seconds=1)
        datetime_patch.now.side_effect = [
            start_time,
            middle_time,
            middle_time,
            middle_time,
            end_time
        ]
        test_key = "test_key"
        with metrics.Timer(test_key) as timer:
            self.assertTrue(isinstance(timer._start_time, datetime))
            metrics_patch.time.assert_not_called()
            timer.send_time()
            metrics_patch.time.assert_called_with(
                test_key,
                (end_time - middle_time).total_seconds()
            )
            second_test_key = "lakshmi_has_toes"
            timer.send_time(second_test_key)
            metrics_patch.time.assert_called_with(
                second_test_key,
                (end_time - middle_time).total_seconds()
            )
            time_delta = timer.get_time_delta()
            self.assertEquals(
                time_delta.total_seconds(),
                (end_time - middle_time).total_seconds()
            )
        metrics_patch.time.assert_called_with(
            test_key,
            (end_time - start_time).total_seconds()
        )


class TestCounterWithTimerContextManager(unittest2.TestCase):
    @patch('st2common.metrics.metrics.datetime')
    @patch('st2common.metrics.metrics.METRICS')
    def test_time(self, metrics_patch, datetime_patch):
        start_time = datetime.now()
        middle_time = start_time + timedelta(seconds=1)
        end_time = middle_time + timedelta(seconds=1)
        datetime_patch.now.side_effect = [
            start_time,
            middle_time,
            middle_time,
            middle_time,
            end_time
        ]
        test_key = "test_key"
        with metrics.CounterWithTimer(test_key) as timer:
            self.assertTrue(isinstance(timer._start_time, datetime))
            metrics_patch.time.assert_not_called()
            timer.send_time()
            metrics_patch.time.assert_called_with(
                "%s%s" % (test_key, METRICS_TIMER_SUFFIX),
                (end_time - middle_time).total_seconds()
            )
            second_test_key = "lakshmi_has_a_nose"
            timer.send_time(second_test_key)
            metrics_patch.time.assert_called_with(
                second_test_key,
                (end_time - middle_time).total_seconds()
            )
            time_delta = timer.get_time_delta()
            self.assertEquals(
                time_delta.total_seconds(),
                (end_time - middle_time).total_seconds()
            )
            metrics_patch.inc_counter.assert_called_with(
                "%s%s" % (test_key, METRICS_COUNTER_SUFFIX)
            )
            metrics_patch.dec_counter.assert_not_called()
        metrics_patch.dec_counter.assert_called_with("%s%s" % (test_key, METRICS_COUNTER_SUFFIX))
        metrics_patch.time.assert_called_with(
            "%s%s" % (test_key, METRICS_TIMER_SUFFIX),
            (end_time - start_time).total_seconds()
        )


class TestCounterWithTimerDecorator(unittest2.TestCase):
    @patch('st2common.metrics.metrics.datetime')
    @patch('st2common.metrics.metrics.METRICS')
    def test_time(self, metrics_patch, datetime_patch):
        start_time = datetime.now()
        middle_time = start_time + timedelta(seconds=1)
        end_time = middle_time + timedelta(seconds=1)
        datetime_patch.now.side_effect = [
            start_time,
            middle_time,
            middle_time,
            middle_time,
            end_time
        ]
        test_key = "test_key"

        @metrics.CounterWithTimer(test_key)
        def _get_tested(metrics_counter_with_timer=None):
            self.assertTrue(isinstance(metrics_counter_with_timer._start_time, datetime))
            metrics_patch.time.assert_not_called()
            metrics_counter_with_timer.send_time()
            metrics_patch.time.assert_called_with(
                "%s%s" % (test_key, METRICS_TIMER_SUFFIX),
                (end_time - middle_time).total_seconds()
            )
            second_test_key = "lakshmi_has_a_nose"
            metrics_counter_with_timer.send_time(second_test_key)
            metrics_patch.time.assert_called_with(
                second_test_key,
                (end_time - middle_time).total_seconds()
            )
            time_delta = metrics_counter_with_timer.get_time_delta()
            self.assertEquals(
                time_delta.total_seconds(),
                (end_time - middle_time).total_seconds()
            )
            metrics_patch.inc_counter.assert_called_with(
                "%s%s" % (test_key, METRICS_COUNTER_SUFFIX)
            )
            metrics_patch.dec_counter.assert_not_called()

        _get_tested()

        metrics_patch.dec_counter.assert_called_with("%s%s" % (test_key, METRICS_COUNTER_SUFFIX))
        metrics_patch.time.assert_called_with(
            "%s%s" % (test_key, METRICS_TIMER_SUFFIX),
            (end_time - start_time).total_seconds()
        )


class TestCounterDecorator(unittest2.TestCase):
    @patch('st2common.metrics.metrics.METRICS')
    def test_counter(self, metrics_patch):
        test_key = "test_key"

        @metrics.Counter(test_key)
        def _get_tested():
            metrics_patch.inc_counter.assert_called_with(test_key)
            metrics_patch.dec_counter.assert_not_called()
        _get_tested()
        metrics_patch.dec_counter.assert_called_with(test_key)


class TestTimerDecorator(unittest2.TestCase):
    @patch('st2common.metrics.metrics.datetime')
    @patch('st2common.metrics.metrics.METRICS')
    def test_time(self, metrics_patch, datetime_patch):
        start_time = datetime.now()
        middle_time = start_time + timedelta(seconds=1)
        end_time = middle_time + timedelta(seconds=1)
        datetime_patch.now.side_effect = [
            start_time,
            middle_time,
            middle_time,
            middle_time,
            end_time
        ]
        test_key = "test_key"

        @metrics.Timer(test_key)
        def _get_tested(metrics_timer=None):
            self.assertTrue(isinstance(metrics_timer._start_time, datetime))
            metrics_patch.time.assert_not_called()
            metrics_timer.send_time()
            metrics_patch.time.assert_called_with(
                test_key,
                (end_time - middle_time).total_seconds()
            )
            second_test_key = "lakshmi_has_toes"
            metrics_timer.send_time(second_test_key)
            metrics_patch.time.assert_called_with(
                second_test_key,
                (end_time - middle_time).total_seconds()
            )
            time_delta = metrics_timer.get_time_delta()
            self.assertEquals(
                time_delta.total_seconds(),
                (end_time - middle_time).total_seconds()
            )
        _get_tested()
        metrics_patch.time.assert_called_with(
            test_key,
            (end_time - start_time).total_seconds()
        )
