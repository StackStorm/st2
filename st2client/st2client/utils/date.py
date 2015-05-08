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

import dateutil.tz
import dateutil.parser

__all__ = [
    'parse',
    'format_isodate'
]


def add_utc_tz(dt):
    return dt.replace(tzinfo=dateutil.tz.tzutc())


def parse(value):
    dt = dateutil.parser.parse(str(value))
    # pylint: disable=no-member
    # For some reason pylint thinks it returns a tuple but it returns a datetime object
    return dt if dt.tzinfo else add_utc_tz(dt)


def format_isodate(value):
    """
    Make a ISO date time string human friendly.

    :type value: ``str``

    :rtype: ``str``
    """
    if not value:
        return ''

    # pylint: disable=no-member
    # For some reason pylint thinks it returns a tuple but it returns a datetime object
    date = dateutil.parser.parse(str(value))
    value = date.strftime('%a, %d %b %Y %H:%M:%S %Z')
    return value
