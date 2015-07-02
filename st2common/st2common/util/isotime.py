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
ISO8601 date related utility functions.
"""

import re
import datetime

from st2common.util import date as date_utils

__all__ = [
    'format',
    'validate',
    'parse'
]


ISO8601_FORMAT = '%Y-%m-%dT%H:%M:%S'
ISO8601_FORMAT_MICROSECOND = '%Y-%m-%dT%H:%M:%S.%f'
ISO8601_UTC_REGEX = \
    '^\d{4}\-\d{2}\-\d{2}(\s|T)\d{2}:\d{2}:\d{2}(\.\d{3,6})?(Z|\+00|\+0000|\+00:00)$'


def format(dt, usec=True, offset=True):
    """
    Format a provided datetime object and return ISO8601 string.

    :type dt: ``datetime.datetime``
    """
    # pylint: disable=no-member
    if isinstance(dt, basestring):
        dt = parse(dt)
    fmt = ISO8601_FORMAT_MICROSECOND if usec else ISO8601_FORMAT
    if offset:
        ost = dt.strftime('%z')
        ost = (ost[:3] + ':' + ost[3:]) if ost else '+00:00'
    else:
        tz = dt.tzinfo.tzname(dt) if dt.tzinfo else 'UTC'
        ost = 'Z' if tz == 'UTC' else tz
    return dt.strftime(fmt) + ost


def validate(value, raise_exception=True):
    if (isinstance(value, datetime.datetime) or
            (type(value) in [str, unicode] and re.match(ISO8601_UTC_REGEX, value))):
        return True
    if raise_exception:
        raise ValueError('Datetime value does not match expected format.')
    return False


def parse(value, preserve_original_tz=False, validate_value=True):
    """
    Parse date in the ISO8601 format and return a time-zone aware datetime object.

    :param value: Date in ISO8601 format.
    :type value: ``str``

    :param preserve_original_tz: True to preserve the original timezone - by default result is
                                 converted into UTC.
    :type preserve_original_tz: ``boolean``

    :param validate_value: True to validate that the date is in the ISO8601 format.
    :type validate_value: ``boolean``

    :rtype: ``datetime.datetime``
    """
    if validate_value:
        validate(value, raise_exception=True)

    dt = date_utils.parse(value=value, preserve_original_tz=preserve_original_tz)
    return dt
