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

from st2common.metrics import base
from st2common.metrics.drivers.statsd_driver import StatsdDriver
from st2common.constants.metrics import METRICS_COUNTER_SUFFIX, METRICS_TIMER_SUFFIX
from st2common.util.date import get_datetime_utc_now

__all__ = [
    'TestBaseMetricsDriver',
    'TestStatsDMetricsDriver',
    'TestCounterContextManager',
    'TestTimerContextManager',
    'TestCounterWithTimerContextManager'
]

cfg.CONF.set_override('driver', 'noop', group='metrics')
cfg.CONF.set_override('host', '127.0.0.1', group='metrics')
cfg.CONF.set_override('port', 8080, group='metrics')


class TestBaseMetricsDriver(unittest2.TestCase):
    _driver = None

    def setUp(self):
        self._driver = base.BaseMetricsDriver()

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

        statsd.Connection.set_defaults.assert_called_once_with(
            host=cfg.CONF.metrics.host,
            port=cfg.CONF.metrics.port
        )

    def test_time(self):
        statsd = MagicMock()
        self._driver._timer = statsd.Timer('')
        params = ('test', 10)
        self._driver.time(*params)
        statsd.Timer().send.assert_called_with(*params)

    def test_time_with_float(self):
        statsd = MagicMock()
        self._driver._timer = statsd.Timer('')
        params = ('test', 10.5)
        self._driver.time(*params)
        statsd.Timer().send.assert_called_with(*params)

    def test_time_with_invalid_key(self):
        params = (2, 2)
        with self.assertRaises(AssertionError):
            self._driver.time(*params)

    def test_time_with_invalid_time(self):
        params = ('test', '1')
        with self.assertRaises(AssertionError):
            self._driver.time(*params)

    @patch('st2common.metrics.drivers.statsd_driver.statsd')
    def test_inc_counter_with_default_amount(self, statsd):
        key = 'test'
        mock_counter = MagicMock()
        statsd.Counter(key).__iadd__.side_effect = mock_counter
        self._driver.inc_counter(key)
        mock_counter.assert_called_once_with(1)

    @patch('st2common.metrics.drivers.statsd_driver.statsd')
    def test_inc_counter_with_amount(self, statsd):
        params = ('test', 2)
        mock_counter = MagicMock()
        statsd.Counter(params[0]).__iadd__.side_effect = mock_counter
        self._driver.inc_counter(*params)
        mock_counter.assert_called_once_with(params[1])

    def test_inc_timer_with_invalid_key(self):
        params = (2, 2)
        with self.assertRaises(AssertionError):
            self._driver.inc_counter(*params)

    def test_inc_timer_with_invalid_amount(self):
        params = ('test', '1')
        with self.assertRaises(AssertionError):
            self._driver.inc_counter(*params)

    @patch('st2common.metrics.drivers.statsd_driver.statsd')
    def test_dec_timer_with_default_amount(self, statsd):
        key = 'test'
        mock_counter = MagicMock()
        statsd.Counter().__isub__.side_effect = mock_counter
        self._driver.dec_counter(key)
        mock_counter.assert_called_once_with(1)

    @patch('st2common.metrics.drivers.statsd_driver.statsd')
    def test_dec_timer_with_amount(self, statsd):
        params = ('test', 2)
        mock_counter = MagicMock()
        statsd.Counter().__isub__.side_effect = mock_counter
        self._driver.dec_counter(*params)
        mock_counter.assert_called_once_with(params[1])

    def test_dec_timer_with_invalid_key(self):
        params = (2, 2)
        with self.assertRaises(AssertionError):
            self._driver.dec_counter(*params)

    def test_dec_timer_with_invalid_amount(self):
        params = ('test', '1')
        with self.assertRaises(AssertionError):
            self._driver.dec_counter(*params)

    @patch('st2common.metrics.drivers.statsd_driver.statsd')
    def test_set_gauge_success(self, statsd):
        params = ('key', 100)
        mock_gauge = MagicMock()
        statsd.Gauge().send.side_effect = mock_gauge
        self._driver.set_gauge(*params)
        mock_gauge.assert_called_once_with(None, params[1])

    @patch('st2common.metrics.drivers.statsd_driver.statsd')
    def test_inc_gauge_success(self, statsd):
        params = ('key1',)
        mock_gauge = MagicMock()
        statsd.Gauge().increment.side_effect = mock_gauge
        self._driver.inc_gauge(*params)
        mock_gauge.assert_called_once_with(None, 1)

        params = ('key2', 100)
        mock_gauge = MagicMock()
        statsd.Gauge().increment.side_effect = mock_gauge
        self._driver.inc_gauge(*params)
        mock_gauge.assert_called_once_with(None, params[1])

    @patch('st2common.metrics.drivers.statsd_driver.statsd')
    def test_dec_gauge_success(self, statsd):
        params = ('key1',)
        mock_gauge = MagicMock()
        statsd.Gauge().decrement.side_effect = mock_gauge
        self._driver.dec_gauge(*params)
        mock_gauge.assert_called_once_with(None, 1)

        params = ('key2', 100)
        mock_gauge = MagicMock()
        statsd.Gauge().decrement.side_effect = mock_gauge
        self._driver.dec_gauge(*params)
        mock_gauge.assert_called_once_with(None, params[1])


class TestCounterContextManager(unittest2.TestCase):
    @patch('st2common.metrics.base.METRICS')
    def test_counter(self, metrics_patch):
        test_key = "test_key"
        with base.Counter(test_key):
            metrics_patch.inc_counter.assert_called_with(test_key)
            metrics_patch.dec_counter.assert_not_called()
        metrics_patch.dec_counter.assert_called_with(test_key)


class TestTimerContextManager(unittest2.TestCase):
    @patch('st2common.metrics.base.get_datetime_utc_now')
    @patch('st2common.metrics.base.METRICS')
    def test_time(self, metrics_patch, datetime_patch):
        start_time = get_datetime_utc_now()
        middle_time = start_time + timedelta(seconds=1)
        end_time = middle_time + timedelta(seconds=1)
        datetime_patch.side_effect = [
            start_time,
            middle_time,
            middle_time,
            middle_time,
            end_time
        ]
        test_key = "test_key"
        with base.Timer(test_key) as timer:
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
    def setUp(self):
        self.start_time = get_datetime_utc_now()
        self.middle_time = self.start_time + timedelta(seconds=1)
        self.end_time = self.middle_time + timedelta(seconds=1)

    @patch('st2common.metrics.base.get_datetime_utc_now')
    @patch('st2common.metrics.base.METRICS')
    def test_time(self, metrics_patch, datetime_patch):
        datetime_patch.side_effect = [
            self.start_time,
            self.middle_time,
            self.middle_time,
            self.middle_time,
            self.end_time
        ]
        test_key = "test_key"
        with base.CounterWithTimer(test_key) as timer:
            self.assertTrue(isinstance(timer._start_time, datetime))
            metrics_patch.time.assert_not_called()
            timer.send_time()
            metrics_patch.time.assert_called_with(
                "%s%s" % (test_key, METRICS_TIMER_SUFFIX),
                (self.end_time - self.middle_time).total_seconds()
            )
            second_test_key = "lakshmi_has_a_nose"
            timer.send_time(second_test_key)
            metrics_patch.time.assert_called_with(
                second_test_key,
                (self.end_time - self.middle_time).total_seconds()
            )
            time_delta = timer.get_time_delta()
            self.assertEquals(
                time_delta.total_seconds(),
                (self.end_time - self.middle_time).total_seconds()
            )
            metrics_patch.inc_counter.assert_called_with(
                "%s%s" % (test_key, METRICS_COUNTER_SUFFIX)
            )
            metrics_patch.dec_counter.assert_not_called()
        metrics_patch.dec_counter.assert_called_with("%s%s" % (test_key, METRICS_COUNTER_SUFFIX))
        metrics_patch.time.assert_called_with(
            "%s%s" % (test_key, METRICS_TIMER_SUFFIX),
            (self.end_time - self.start_time).total_seconds()
        )


class TestCounterWithTimerDecorator(unittest2.TestCase):
    @patch('st2common.metrics.base.get_datetime_utc_now')
    @patch('st2common.metrics.base.METRICS')
    def test_time(self, metrics_patch, datetime_patch):
        start_time = get_datetime_utc_now()
        middle_time = start_time + timedelta(seconds=1)
        end_time = middle_time + timedelta(seconds=1)
        datetime_patch.side_effect = [
            start_time,
            middle_time,
            middle_time,
            middle_time,
            end_time
        ]
        test_key = "test_key"

        @base.CounterWithTimer(test_key, include_parameter=True)
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
    @patch('st2common.metrics.base.METRICS')
    def test_counter(self, metrics_patch):
        test_key = "test_key"

        @base.Counter(test_key)
        def _get_tested():
            metrics_patch.inc_counter.assert_called_with(test_key)
            metrics_patch.dec_counter.assert_not_called()
        _get_tested()
        metrics_patch.dec_counter.assert_called_with(test_key)


class TestTimerDecorator(unittest2.TestCase):
    @patch('st2common.metrics.base.get_datetime_utc_now')
    @patch('st2common.metrics.base.METRICS')
    def test_time(self, metrics_patch, datetime_patch):
        start_time = get_datetime_utc_now()
        middle_time = start_time + timedelta(seconds=1)
        end_time = middle_time + timedelta(seconds=1)
        datetime_patch.side_effect = [
            start_time,
            middle_time,
            middle_time,
            middle_time,
            end_time
        ]
        test_key = "test_key"

        @base.Timer(test_key)
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


class TestFormatMetrics(unittest2.TestCase):
    def test_format_metrics_liveaction_db_without_key(self):
        pack = 'test'
        action = 'lakface'

        liveaction_db = MagicMock()
        liveaction_db.context = {'pack': pack}
        liveaction_db.action = action

        key = base.format_metrics_key(liveaction_db=liveaction_db)

        self.assertEquals(key, "st2.%s.%s" % (pack, action))

    def test_format_metrics_liveaction_db_with_key(self):
        pack = 'test'
        action = 'lakface'
        test_key = 'meh'

        liveaction_db = MagicMock()
        liveaction_db.context = {'pack': pack}
        liveaction_db.action = "%s.%s" % (pack, action)

        key = base.format_metrics_key(liveaction_db=liveaction_db, key=test_key)

        self.assertEquals(key, "st2.%s.%s.%s" % (pack, action, test_key))

    def test_format_metrics_liveaction_db_without_pack(self):
        action = 'lakface'
        pack = 'unknown'

        liveaction_db = MagicMock()
        liveaction_db.context = {}
        liveaction_db.action = "%s.%s" % (pack, action)

        key = base.format_metrics_key(liveaction_db=liveaction_db)

        self.assertEquals(key, "st2.%s.%s" % (pack, action))

    def test_format_metrics_action_db_without_key(self):
        pack = 'test'
        action = 'lakface'

        action_db = MagicMock()
        action_db.pack = pack
        action_db.name = action

        key = base.format_metrics_key(action_db=action_db)

        self.assertEquals(key, "st2.%s.%s" % (pack, action))

    def test_format_metrics_action_db_with_key(self):
        pack = 'test'
        action = 'lakface'
        test_key = 'meh'

        action_db = MagicMock()
        action_db.pack = pack
        action_db.name = action

        key = base.format_metrics_key(action_db=action_db, key=test_key)

        self.assertEquals(key, "st2.%s.%s.%s" % (pack, action, test_key))

    def test_format_metrics_action_db_without_pack(self):
        action = 'lakface'
        pack = 'unknown'

        action_db = MagicMock()
        action_db.pack = None
        action_db.name = action

        key = base.format_metrics_key(action_db=action_db)

        self.assertEquals(key, "st2.%s.%s" % (pack, action))
