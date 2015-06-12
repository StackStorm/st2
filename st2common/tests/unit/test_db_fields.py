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

import time
import datetime
import calendar

import mock
import unittest2

from st2common.fields import ComplexDateTimeField
from st2common.util import isotime


class ComplexDateTimeFieldTestCase(unittest2.TestCase):
    def test_what_comes_in_goes_out(self):
        field = ComplexDateTimeField()

        date = datetime.datetime.utcnow()
        date = isotime.add_utc_tz(date)

        us = field._datetime_to_microseconds_since_epoch(date)
        result = field._microseconds_since_epoch_to_datetime(us)
        self.assertEqual(date, result)

    def test_round_trip_conversion(self):
        datetime_values = [
            datetime.datetime(2015, 1, 1, 15, 0, 0).replace(microsecond=500),
            datetime.datetime(2015, 1, 1, 15, 0, 0).replace(microsecond=0),
            datetime.datetime(2015, 1, 1, 15, 0, 0).replace(microsecond=999999)
        ]
        datetime_values = [
            isotime.add_utc_tz(datetime_values[0]),
            isotime.add_utc_tz(datetime_values[1]),
            isotime.add_utc_tz(datetime_values[2])
        ]
        microsecond_values = []

        # Calculate microsecond values
        for value in datetime_values:
            seconds = calendar.timegm(value.timetuple())
            microseconds_reminder = value.time().microsecond
            result = int(seconds * 1000000) + microseconds_reminder
            microsecond_values.append(result)

        field = ComplexDateTimeField()
        # datetime to us
        for index, value in enumerate(datetime_values):
            actual_value = field._datetime_to_microseconds_since_epoch(value=value)
            expected_value = microsecond_values[index]
            expected_microseconds = value.time().microsecond

            self.assertEqual(actual_value, expected_value)
            self.assertTrue(str(actual_value).endswith(str(expected_microseconds)))

        # us to datetime
        for index, value in enumerate(microsecond_values):
            actual_value = field._microseconds_since_epoch_to_datetime(data=value)
            expected_value = datetime_values[index]
            self.assertEqual(actual_value, expected_value)

    @mock.patch('st2common.fields.LongField.__get__')
    def test_get_(self, mock_get):
        field = ComplexDateTimeField()

        # No value set
        mock_get.return_value = None
        self.assertEqual(field.__get__(instance=None, owner=None), None)

        # Already a datetime
        mock_get.return_value = datetime.datetime.now()
        self.assertEqual(field.__get__(instance=None, owner=None), mock_get.return_value)

        # Microseconds
        dt = datetime.datetime(2015, 1, 1, 15, 0, 0).replace(microsecond=500)
        dt = isotime.add_utc_tz(dt)
        us = field._datetime_to_microseconds_since_epoch(value=dt)
        mock_get.return_value = us
        self.assertEqual(field.__get__(instance=None, owner=None), dt)
