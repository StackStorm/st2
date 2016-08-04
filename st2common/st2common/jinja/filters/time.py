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


def to_human_time_from_seconds(time_seconds):
    """
    Given a time value in seconds, this function returns
    a fuzzy version like 3m5s.

    :param time_seconds: Time specified in seconds.
    :type time_seconds: ``int`` or ``long``

    :rtype: ``str``
    """
    assert time_seconds is int or time_seconds is long
    timedelta_str = datetime.timedelta(seconds=time_seconds)  # Returns 'hh:mm:ss'
    return _get_human_time(timedelta_str)


def _get_human_time(timedelta_str):
    """
    Takes a timedelta string of form '01:03:05' and returns a string
    of form '1h3m5s'.

    :param timedelta_str: Timedelta in string format.
    :type timedelta_str: ``str``

    :rtype: ``str``
    """
    time_parts = timedelta_str.split(':')
    time_parts = [part.lstrip("0") for part in time_parts]
    return '%sh%sm%ss' % (tuple(time_parts))
