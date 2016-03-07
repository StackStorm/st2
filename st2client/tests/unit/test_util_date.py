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

import mock
import unittest2

from st2client.utils.date import add_utc_tz
from st2client.utils.date import format_dt
from st2client.utils.date import format_isodate
from st2client.utils.date import format_isodate_for_user_timezone


class DateUtilsTestCase(unittest2.TestCase):
    def test_format_dt(self):
        dt = datetime.datetime(2015, 10, 20, 8, 0, 0)
        dt = add_utc_tz(dt)
        result = format_dt(dt)
        self.assertEqual(result, 'Tue, 20 Oct 2015 08:00:00 UTC')

    def test_format_isodate(self):
        # No timezone, defaults to UTC
        value = 'Tue, 20 Oct 2015 08:00:00 UTC'
        result = format_isodate(value=value)
        self.assertEqual(result, 'Tue, 20 Oct 2015 08:00:00 UTC')

        # Timezone provided
        value = 'Tue, 20 Oct 2015 08:00:00 UTC'
        result = format_isodate(value=value, timezone='Europe/Ljubljana')
        self.assertEqual(result, 'Tue, 20 Oct 2015 10:00:00 CEST')

    @mock.patch('st2client.utils.date.get_config')
    def test_format_isodate_for_user_timezone(self, mock_get_config):
        # No timezone, defaults to UTC
        mock_get_config.return_value = {}

        value = 'Tue, 20 Oct 2015 08:00:00 UTC'
        result = format_isodate_for_user_timezone(value=value)
        self.assertEqual(result, 'Tue, 20 Oct 2015 08:00:00 UTC')

        # Timezone provided
        mock_get_config.return_value = {'cli': {'timezone': 'Europe/Ljubljana'}}

        value = 'Tue, 20 Oct 2015 08:00:00 UTC'
        result = format_isodate_for_user_timezone(value=value)
        self.assertEqual(result, 'Tue, 20 Oct 2015 10:00:00 CEST')
