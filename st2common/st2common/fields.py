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
import enum

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

# Delimiter field used for actual JSON dict field binary value
JSON_DICT_FIELD_DELIMITER = b":"


class JSONDictFieldCompressionAlgorithmEnum(enum.Enum):
    """
    Enum which represents compression algorithm (if any) used for a specific JSONDictField value.
    """
    NONE = b"n"
    ZSTANDARD = b"z"


class JSONDictFieldSerializationFormatEnum(enum.Enum):
    """
    Enum which represents serialization format used for a specific JSONDictField value.
    """
    ORJSON = b"o"


VALID_JSON_DICT_COMPRESSION_ALGORITHMS = [
    JSONDictFieldCompressionAlgorithmEnum.NONE.value,
    JSONDictFieldCompressionAlgorithmEnum.ZSTANDARD.value,
]


VALID_JSON_DICT_SERIALIZATION_FORMATS = [
    JSONDictFieldSerializationFormatEnum.ORJSON.value,
]


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

    def _parse_field_value(self, value: bytes) -> dict:
        """
        Parse provided binary field value and return a tuple with (compression_flag,
        serialization_format_name, binary_data).

        For example:

            - (n, o, ...) - no compression, data is serialized using orjson
            - (z, o, ...) - zstandard compression, data is serialized using orjson
        """
        if not self.use_header:
            return orjson.loads(value)

        split = value.split(JSON_DICT_FIELD_DELIMITER, 2)

        if len(split) != 3:
            raise ValueError("Expected 3 values when splitting field value, got %s" % (len(split)))

        compression_algorithm = split[0]
        serialization_format = split[1]
        data = split[2]

        if compression_algorithm not in VALID_JSON_DICT_COMPRESSION_ALGORITHMS:
            raise ValueError("Invalid or unsupported value for compression algorithm header "
                             "value: %s" % (compression_algorithm))

        if serialization_format not in VALID_JSON_DICT_SERIALIZATION_FORMATS:
            raise ValueError("Invalid or unsupported value for serialization format header "
                             "value: %s" % (serialization_format))

        if compression_algorithm == JSONDictFieldCompressionAlgorithmEnum.ZSTANDARD.value:
            data = zstandard.ZstdDecompressor().decompress(data)

        data = orjson.loads(data)
        return data

    def _serialize_field_value(self, value: dict) -> bytes:
        """
        Serialize and encode the provided field value.
        """
        if not self.use_header:
            return orjson.dumps(value)

        data = orjson.dumps(value)

        if self.compression_algorithm == "zstandard":
            compression_header = JSONDictFieldCompressionAlgorithmEnum.ZSTANDARD
            data = zstandard.ZstdCompressor().compress(data)
        else:
            compression_header = JSONDictFieldCompressionAlgorithmEnum.NONE

        return compression_header.value + b":" + b"o:" + data

    def __init__(self, *args, **kwargs):
        # True if we should use field header which is more future proof approach and also allows
        # us to support optional per-field compression, etc.
        # This option is only exposed so we can benchmark different approaches and how much overhead
        # using a header adds.
        self.use_header = kwargs.pop('use_header', False)
        self.compression_algorithm = kwargs.pop('compression_algorithm', "none")

        super(JSONDictField, self).__init__(*args, **kwargs)

        self.json_loads = orjson.loads
        self.json_dumps = orjson.dumps

    def to_mongo(self, value):
        if not isinstance(value, dict):
            raise ValueError('value argument must be a dictionary')

        data = self._serialize_field_value(value)
        return data

    def to_python(self, value):
        if isinstance(value, dict):
            # Already parsed
            return value

        data = self._parse_field_value(value)
        return data

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
        if not isinstance(value, dict):
            raise ValueError('value argument must be a dictionary (got: %s)' % type(value))

        return self._serialize_field_value(value)

    def to_python(self, value):
        if isinstance(value, dict):
            # Old format which used a native dict with escaped special characters
            value = mongoescape.unescape_chars(value)
            return value

        if isinstance(value, (six.text_type, six.binary_type)):
            return self._parse_field_value(value)

        return value
