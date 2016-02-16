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

"""
Date related utility functions.
"""

import datetime

import dateutil.tz
import dateutil.parser


__all__ = [
    'get_datetime_utc_now',
    'add_utc_tz',
    'convert_to_utc',
    'parse'
]


def get_datetime_utc_now():
    """
    Retrieve datetime object for current time with included UTC timezone info.

    :rtype: ``datetime.datetime``
    """
    dt = datetime.datetime.utcnow()
    dt = add_utc_tz(dt)
    return dt


def add_utc_tz(dt):
    if dt.tzinfo and dt.tzinfo.utcoffset(dt) != datetime.timedelta(0):
        raise ValueError('datetime already contains a non UTC timezone')

    return dt.replace(tzinfo=dateutil.tz.tzutc())


def convert_to_utc(dt):
    """
    Convert provided datetime object to UTC timezone.

    Note: If the object has no timezone information we assume it's in UTC.

    :rtype: ``datetime.datetime``
    """
    if not dt.tzinfo:
        return add_utc_tz(dt)

    dt = dt.astimezone(dateutil.tz.tzutc())
    return dt


def parse(value, preserve_original_tz=False):
    """
    Parse a date string and return a time-zone aware datetime object.

    :param value: Date in ISO8601 format.
    :type value: ``str``

    :param preserve_original_tz: True to preserve the original timezone - by default result is
                                 converted into UTC.
    :type preserve_original_tz: ``boolean``

    :rtype: ``datetime.datetime``
    """
    dt = dateutil.parser.parse(str(value))

    if not dt.tzinfo:
        dt = add_utc_tz(dt)

    if not preserve_original_tz:
        dt = convert_to_utc(dt)

    return dt
