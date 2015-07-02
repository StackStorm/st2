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

import datetime

import pytz
import unittest2

from st2common.util import date as date_utils


class DateUtilsTestCase(unittest2.TestCase):
    def test_get_datetime_utc_now(self):
        date = date_utils.get_datetime_utc_now()
        self.assertEqual(date.tzinfo.tzname(None), 'UTC')

    def test_add_utc_tz(self):
        dt = datetime.datetime.utcnow()
        self.assertIsNone(dt.tzinfo)
        dt = date_utils.add_utc_tz(dt)
        self.assertIsNotNone(dt.tzinfo)
        self.assertEqual(dt.tzinfo.tzname(None), 'UTC')

    def test_convert_to_utc(self):
        date_without_tz = datetime.datetime.utcnow()
        self.assertEqual(date_without_tz.tzinfo, None)
        result = date_utils.convert_to_utc(date_without_tz)
        self.assertEqual(result.tzinfo.tzname(None), 'UTC')

        date_with_pdt_tz = datetime.datetime(2015, 10, 28, 10, 0, 0, 0)
        date_with_pdt_tz = date_with_pdt_tz.replace(tzinfo=pytz.timezone('US/Pacific'))
        self.assertEqual(date_with_pdt_tz.tzinfo.tzname(None), 'US/Pacific')

        result = date_utils.convert_to_utc(date_with_pdt_tz)
        self.assertEqual(str(result), '2015-10-28 17:53:00+00:00')
        self.assertEqual(result.tzinfo.tzname(None), 'UTC')

    def test_parse(self):
        date_str_without_tz = 'January 1st, 2014 10:00:00'
        result = date_utils.parse(value=date_str_without_tz)
        self.assertEqual(str(result), '2014-01-01 10:00:00+00:00')
        self.assertEqual(result.tzinfo.tzname(None), 'UTC')

        # preserve original tz
        date_str_with_tz = 'January 1st, 2014 10:00:00 +07:00'
        result = date_utils.parse(value=date_str_with_tz, preserve_original_tz=True)
        self.assertEqual(str(result), '2014-01-01 10:00:00+07:00')
        self.assertEqual(result.tzinfo.utcoffset(result), datetime.timedelta(hours=7))

        # convert to utc
        date_str_with_tz = 'January 1st, 2014 10:00:00 +07:00'
        result = date_utils.parse(value=date_str_with_tz, preserve_original_tz=False)
        self.assertEqual(str(result), '2014-01-01 03:00:00+00:00')
        self.assertEqual(result.tzinfo.utcoffset(result), datetime.timedelta(hours=0))
        self.assertEqual(result.tzinfo.tzname(None), 'UTC')
