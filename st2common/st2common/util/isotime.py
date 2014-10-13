import re
import datetime

import dateutil.tz
import dateutil.parser


ISO8601_FORMAT = '%Y-%m-%dT%H:%M:%S'
ISO8601_FORMAT_MICROSECOND = '%Y-%m-%dT%H:%M:%S.%f'
ISO8601_UTC_REGEX = '^\d{4}-\d{2}-\d{2}(\s|T)\d{2}:\d{2}:\d{2}(.\d{6})?(Z|\+00|\+0000|\+00:00)$'


def add_utc_tz(dt):
    return dt.replace(tzinfo=dateutil.tz.tzutc())


def format(dt, usec=True, offset=True):
    if type(dt) in [str, unicode]:
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


def parse(value):
    validate(value, raise_exception=True)
    dt = dateutil.parser.parse(str(value))
    return dt if dt.tzinfo else add_utc_tz(dt)
