# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import

import datetime
import calendar

import six
import orjson
import zstandard

from mongoengine import LongField
from mongoengine import BinaryField

from st2common.util import date as date_utils
from st2common.util import mongoescape

__all__ = [
    'ComplexDateTimeField'
]

SECOND_TO_MICROSECONDS = 1000000


class ComplexDateTimeField(LongField):
    """
    Date time field which handles microseconds exactly and internally stores
    the timestamp as number of microseconds since the unix epoch.

    Note: We need to do that because mongoengine serializes this field as comma
    delimited string which breaks sorting.
    """

    def _convert_from_datetime(self, val):
        """
        Convert a `datetime` object to number of microseconds since epoch representation
        (which will be stored in MongoDB). This is the reverse function of
        `_convert_from_db`.
        """
        result = self._datetime_to_microseconds_since_epoch(value=val)
        return result

    def _convert_from_db(self, value):
        result = self._microseconds_since_epoch_to_datetime(data=value)
        return result

    def _microseconds_since_epoch_to_datetime(self, data):
        """
        Convert a number representation to a `datetime` object (the object you
        will manipulate). This is the reverse function of
        `_convert_from_datetime`.

        :param data: Number of microseconds since the epoch.
        :type data: ``int``
        """
        result = datetime.datetime.utcfromtimestamp(data // SECOND_TO_MICROSECONDS)
        microseconds_reminder = (data % SECOND_TO_MICROSECONDS)
        result = result.replace(microsecond=microseconds_reminder)
        result = date_utils.add_utc_tz(result)
        return result

    def _datetime_to_microseconds_since_epoch(self, value):
        """
        Convert datetime in UTC to number of microseconds from epoch.

        Note: datetime which is passed to the function needs to be in UTC timezone (e.g. as returned
        by ``datetime.datetime.utcnow``).

        :rtype: ``int``
        """
        # Verify that the value which is passed in contains UTC timezone
        # information.
        if not value.tzinfo or (value.tzinfo.utcoffset(value) != datetime.timedelta(0)):
            raise ValueError('Value passed to this function needs to be in UTC timezone')

        seconds = calendar.timegm(value.timetuple())
        microseconds_reminder = value.time().microsecond
        result = (int(seconds * SECOND_TO_MICROSECONDS) + microseconds_reminder)
        return result

    def __get__(self, instance, owner):
        data = super(ComplexDateTimeField, self).__get__(instance, owner)
        if data is None:
            return None
        if isinstance(data, datetime.datetime):
            return data
        return self._convert_from_db(data)

    def __set__(self, instance, value):
        value = self._convert_from_datetime(value) if value else value
        return super(ComplexDateTimeField, self).__set__(instance, value)

    def validate(self, value):
        value = self.to_python(value)
        if not isinstance(value, datetime.datetime):
            self.error('Only datetime objects may used in a '
                       'ComplexDateTimeField')

    def to_python(self, value):
        original_value = value
        try:
            return self._convert_from_db(value)
        except:
            return original_value

    def to_mongo(self, value):
        value = self.to_python(value)
        return self._convert_from_datetime(value)

    def prepare_query_value(self, op, value):
        return self._convert_from_datetime(value)


class JSONDictField(BinaryField):
    """
    Custom field types which stores dictionary as JSON serialized strings.

    This is done because storing large objects as JSON serialized strings is much more fficient
    on the serialize and unserialize paths compared to used EscapedDictField which needs to escape
    all the special values ($, .).

    Only downside is that to MongoDB those values are plain raw strings which means you can't query
    on actual dictionary field values. That's not an issue for us, because in places where we use
    it, those values are already treated as plain binary blobs to the database layer and we never
    directly query on those field values.

    In micro benchmarks we have seen speed ups for up to 10x on write path and up to 6x on read
    path. Change also scaled down which means it didn't add any additional overhead for very small
    results - in fact, it was also faster for small results dictionaries

    More context and numbers are available at https://github.com/StackStorm/st2/pull/4846.
    """

    def __init__(self, *args, **kwargs):
        self.compression_algorithm = kwargs.pop('compression_algorithm', 'none')

        super(JSONDictField, self).__init__(*args, **kwargs)

        self.json_loads = orjson.loads
        self.json_dumps = orjson.dumps

    def to_mongo(self, value):
        if not isinstance(value, dict):
            raise ValueError('value argument must be a dictionary')

        data = self.json_dumps(value)

        if self.compression_algorithm == "zstandard":
            cctx = zstandard.ZstdCompressor()
            data = cctx.compress(data)

        return data

    def to_python(self, value):
        if isinstance(value, (six.text_type, six.binary_type)):
            if self.compression_algorithm == "zstandard":
                data = zstandard.ZstdDecompressor().decompress(value)
            else:
                data = value

            return self.json_loads(data)

        return value

    def validate(self, value):
        value = self.to_mongo(value)
        return super(JSONDictField, self).validate(value)


class JSONDictEscapedFieldCompatibilityField(JSONDictField):
    """
    Special version of JSONDictField which takes care of compatibility between old EscapedDictField
    and EscapedDynamicField format and the new one.

    On retrieval, if an old format is detected it's correctly un-serialized and on insertion, we
    always insert data in a new format.
    """

    def to_mongo(self, value):
        if isinstance(value, six.binary_type):
            # Already serialized
            return value

        if not isinstance(value, dict):
            raise ValueError('value argument must be a dictionary (got: %s)' % type(value))

        return self.json_dumps(value)

    def to_python(self, value):
        if isinstance(value, dict):
            # Old format which used a native dict with escaped special characters
            value = mongoescape.unescape_chars(value)
            return value

        if isinstance(value, (six.text_type, six.binary_type)):
            return self.json_loads(value)

        return value
