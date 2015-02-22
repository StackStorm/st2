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

import unittest2

from st2common.fields import ComplexDateTimeField


class ComplexDateTimeFieldTestCase(unittest2.TestCase):
    def test_round_trip_conversion(self):
        datetime_values = [
            datetime.datetime(2015, 1, 1, 15, 0, 0).replace(microsecond=500),
            datetime.datetime(2015, 1, 1, 15, 0, 0).replace(microsecond=0),
            datetime.datetime(2015, 1, 1, 15, 0, 0).replace(microsecond=999999)
        ]
        microsecond_values = []

        # Calculate microsecond values
        for value in datetime_values:
            seconds = time.mktime(value.timetuple())
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
