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

__all__ = [
    'to_human_time_from_seconds'
]


def to_human_time_from_seconds(seconds):
    """
    Given a time value in seconds, this function returns
    a fuzzy version like 3m5s.

    :param time_seconds: Time specified in seconds.
    :type time_seconds: ``int`` or ``long`` or ``float``

    :rtype: ``str``
    """
    assert (isinstance(seconds, int) or isinstance(seconds, long) or
            isinstance(seconds, float))

    return _get_human_time(seconds)


def _get_human_time(seconds):
    """
    Takes number of seconds as input and returns a string of form '1h3m5s'.

    :param seconds: Number of seconds.
    :type seconds: ``int`` or ``long`` or ``float``

    :rtype: ``str``
    """

    if seconds is None:
        return None

    if seconds == 0:
        return '0s'

    if seconds < 1:
        return '%s\u03BCs' % seconds  # Microseconds

    if isinstance(seconds, float):
        seconds = long(round(seconds))  # Let's lose microseconds.

    timedelta = datetime.timedelta(seconds=seconds)
    offset_date = datetime.datetime(1, 1, 1) + timedelta

    years = offset_date.year - 1
    days = offset_date.day - 1
    hours = offset_date.hour
    mins = offset_date.minute
    secs = offset_date.second

    time_parts = [years, days, hours, mins, secs]

    first_non_zero_pos = next((i for i, x in enumerate(time_parts) if x), None)

    if first_non_zero_pos is None:
        return '0s'
    else:
        time_parts = time_parts[first_non_zero_pos:]

    if len(time_parts) == 1:
        return '%ss' % tuple(time_parts)
    elif len(time_parts) == 2:
        return '%sm%ss' % tuple(time_parts)
    elif len(time_parts) == 3:
        return '%sh%sm%ss' % tuple(time_parts)
    elif len(time_parts) == 4:
        return '%sd%sh%sm%ss' % tuple(time_parts)
    elif len(time_parts) == 5:
        return '%sy%sd%sh%sm%ss' % tuple(time_parts)
