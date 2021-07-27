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

"""
NOTE: BaseList and BaseDict classes below are based on mongoengine code from
https://github.com/MongoEngine/mongoengine/blob/master/mongoengine/base/datastructures.py

Mongoengine is licensed under MIT.
"""

from __future__ import absolute_import

from typing import Optional
from typing import Union

import datetime
import calendar
import enum
import weakref

import orjson

from mongoengine import LongField
from mongoengine import BinaryField
from mongoengine.base.datastructures import mark_as_changed_wrapper
from mongoengine.base.datastructures import mark_key_as_changed_wrapper
from mongoengine.common import _import_class

from st2common.util import date as date_utils
from st2common.util import mongoescape

__all__ = ["ComplexDateTimeField"]

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
        microseconds_reminder = data % SECOND_TO_MICROSECONDS
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
            raise ValueError(
                "Value passed to this function needs to be in UTC timezone"
            )

        seconds = calendar.timegm(value.timetuple())
        microseconds_reminder = value.time().microsecond
        result = int(seconds * SECOND_TO_MICROSECONDS) + microseconds_reminder
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
            self.error("Only datetime objects may used in a " "ComplexDateTimeField")

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


class BaseList(list):
    """
    Custom list class based on mongoengine.base.datastructures.BaseDict which acts as a
    wrapper for list value for JSONDictField which allows us to track changes to the list items.

    Tracking changes to the list is important since it allows us to implement more efficient
    partial document updates - e.g. if field A on model to be updated hasn't changed, actual
    database save operation will only write out field which values have changed.

    This works exactly in the same manner mongoengine DictField and DynamicField.
    """

    _instance = None
    _name = None

    def __init__(self, list_items, instance, name):
        BaseDocument = _import_class("BaseDocument")

        if isinstance(instance, BaseDocument):
            self._instance = weakref.proxy(instance)

        self._name = name
        super().__init__(list_items)

    def __getitem__(self, key):
        # change index to positive value because MongoDB does not support negative one
        if isinstance(key, int) and key < 0:
            key = len(self) + key
        value = super().__getitem__(key)

        if isinstance(key, slice):
            # When receiving a slice operator, we don't convert the structure and bind
            # to parent's instance. This is buggy for now but would require more work to be handled
            # properly
            return value

        if isinstance(value, dict) and not isinstance(value, BaseDict):
            # Replace dict by BaseDict
            value = BaseDict(value, None, f"{self._name}.{key}")
            super().__setitem__(key, value)
            value._instance = self._instance
        elif isinstance(value, list) and not isinstance(value, BaseList):
            # Replace list by BaseList
            value = BaseList(value, None, f"{self._name}.{key}")
            super().__setitem__(key, value)
            value._instance = self._instance
        return value

    def __iter__(self):
        yield from super().__iter__()

    def __getstate__(self):
        self.instance = None
        return self

    def __setstate__(self, state):
        self = state
        return self

    def __setitem__(self, key, value):
        changed_key = key
        if isinstance(key, slice):
            # In case of slice, we don't bother to identify the exact elements being updated
            # instead, we simply marks the whole list as changed
            changed_key = None

        result = super().__setitem__(key, value)
        self._mark_as_changed(changed_key)
        return result

    append = mark_as_changed_wrapper(list.append)
    extend = mark_as_changed_wrapper(list.extend)
    insert = mark_as_changed_wrapper(list.insert)
    pop = mark_as_changed_wrapper(list.pop)
    remove = mark_as_changed_wrapper(list.remove)
    reverse = mark_as_changed_wrapper(list.reverse)
    sort = mark_as_changed_wrapper(list.sort)
    __delitem__ = mark_as_changed_wrapper(list.__delitem__)
    __iadd__ = mark_as_changed_wrapper(list.__iadd__)
    __imul__ = mark_as_changed_wrapper(list.__imul__)

    def _mark_as_changed(self, key=None):
        if hasattr(self._instance, "_mark_as_changed"):
            # Since our type is a special binary type, we always mark top level dict as changes
            # since whole dict needs to be saved at once, we can't update just a singel dict
            # item.
            parent_key_name = self._name.split(".")[0]
            self._instance._mark_as_changed(parent_key_name)


class BaseDict(dict):
    """
    Custom dictionary class based on mongoengine.base.datastructures.BaseDict which acts as a
    wrapper for dict value for JSONDictField which allows us to track changes to the dict.

    Tracking changes to the dict is important since it allows us to implement more efficient
    partial document updates - e.g. if field A on model to be updated hasn't changed, actual
    database save operation will only write out field which values have changed.

    This works exactly in the same manner mongoengine DictField and DynamicField.
    """

    _instance = None
    _name = None

    def __init__(self, dict_items, instance, name):
        BaseDocument = _import_class("BaseDocument")

        if isinstance(instance, BaseDocument):
            self._instance = weakref.proxy(instance)

        self._name = name
        super().__init__(dict_items)

    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default

    def __getitem__(self, key):
        value = super().__getitem__(key)

        if isinstance(value, dict) and not isinstance(value, BaseDict):
            value = BaseDict(value, None, f"{self._name}.{key}")
            super().__setitem__(key, value)
            value._instance = self._instance
        # We also need to return a wrapper class in case of a list to ensure updates o the
        # list items are correctly racked
        elif isinstance(value, list) and not isinstance(value, BaseList):
            value = BaseList(value, None, f"{self._name}.{key}")
            super().__setitem__(key, value)
            value._instance = self._instance

        return value

    def __getstate__(self):
        self.instance = None
        return self

    def __setstate__(self, state):
        self = state
        return self

    __setitem__ = mark_key_as_changed_wrapper(dict.__setitem__)
    __delattr__ = mark_key_as_changed_wrapper(dict.__delattr__)
    __delitem__ = mark_key_as_changed_wrapper(dict.__delitem__)
    pop = mark_as_changed_wrapper(dict.pop)
    clear = mark_as_changed_wrapper(dict.clear)
    update = mark_as_changed_wrapper(dict.update)
    popitem = mark_as_changed_wrapper(dict.popitem)
    setdefault = mark_as_changed_wrapper(dict.setdefault)

    def _mark_as_changed(self, key=None):
        if hasattr(self._instance, "_mark_as_changed"):
            # Since our type is a special binary type, we always mark top level dict as changes
            # since whole dict needs to be saved at once, we can't update just a singel dict
            # item.
            parent_key_name = self._name.split(".")[0]
            self._instance._mark_as_changed(parent_key_name)


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

    NOTES, LIMITATIONS:

    This field type can only be used on dictionary values on which we don't perform direct database
    queries (aka filter on a specific dictionary item value or similar).

    Good examples of those are "result" field on ExecutionDB, LiveActionDB and TaskExecutionDB,
    "output" on WorkflowExecutionDB, etc.

    IMPLEMENTATION DETAILS:

    If header is used, values are stored in the following format:
        <compression type>:<serialization type>:<serialized binary data>.

    For example:

        n:o:... - No compression, (or)json serialization
        z:o:... - Zstandard compression, (or)json serialization

    If header is not used, value is stored as a serialized JSON string of the input dictionary.
    """

    def __init__(self, *args, **kwargs):
        # True if we should use field header which is more future proof approach and also allows
        # us to support optional per-field compression, etc.
        # This option is only exposed so we can benchmark different approaches and how much overhead
        # using a header adds.
        self.use_header = kwargs.pop("use_header", False)
        self.compression_algorithm = kwargs.pop("compression_algorithm", "none")

        super(JSONDictField, self).__init__(*args, **kwargs)

    def to_mongo(self, value):
        if not isinstance(value, dict):
            raise ValueError(
                "value argument must be a dictionary (got: %s)" % type(value)
            )

        data = self._serialize_field_value(value)
        return data

    def to_python(self, value):
        if isinstance(value, dict):
            # Already parsed
            return value

        data = self.parse_field_value(value)
        return data

    def validate(self, value):
        value = self.to_mongo(value)
        return super(JSONDictField, self).validate(value)

    def parse_field_value(self, value: Optional[Union[bytes, dict]]) -> dict:
        """
        Parse provided binary field value and return parsed value (dictionary).

        For example:

            - (n, o, ...) - no compression, data is serialized using orjson
            - (z, o, ...) - zstandard compression, data is serialized using orjson
        """
        if not value:
            return self.default

        if isinstance(value, dict):
            # Already deserializaed
            return value

        if not self.use_header:
            return orjson.loads(value)

        split = value.split(JSON_DICT_FIELD_DELIMITER, 2)

        if len(split) != 3:
            raise ValueError(
                "Expected 3 values when splitting field value, got %s" % (len(split))
            )

        compression_algorithm = split[0]
        serialization_format = split[1]
        data = split[2]

        if compression_algorithm not in VALID_JSON_DICT_COMPRESSION_ALGORITHMS:
            raise ValueError(
                "Invalid or unsupported value for compression algorithm header "
                "value: %s" % (compression_algorithm)
            )

        if serialization_format not in VALID_JSON_DICT_SERIALIZATION_FORMATS:
            raise ValueError(
                "Invalid or unsupported value for serialization format header "
                "value: %s" % (serialization_format)
            )

        if (
            compression_algorithm
            == JSONDictFieldCompressionAlgorithmEnum.ZSTANDARD.value
        ):
            # NOTE: At this point zstandard is only test dependency
            import zstandard

            data = zstandard.ZstdDecompressor().decompress(data)

        data = orjson.loads(data)
        return data

    def _serialize_field_value(self, value: dict) -> bytes:
        """
        Serialize and encode the provided field value.
        """
        # Orquesta workflows support toSet() YAQL operator which returns a set which used to get
        # serialized to list by mongoengine DictField.
        #
        # For backward compatibility reasons, we need to support serializing set to a list as
        # well.
        #
        # Based on micro benchmarks, using default function adds very little overhead (1%) so it
        # should be safe to use default for every operation.
        #
        # If this turns out to be not true or it adds more overhead in other scenarios, we should
        # revisit this decision and only use "default" argument where needed (aka Workflow models).
        def default(obj):
            if isinstance(obj, set):
                return list(obj)
            raise TypeError

        if not self.use_header:
            return orjson.dumps(value, default=default)

        data = orjson.dumps(value, default=default)

        if self.compression_algorithm == "zstandard":
            # NOTE: At this point zstandard is only test dependency
            import zstandard

            compression_header = JSONDictFieldCompressionAlgorithmEnum.ZSTANDARD
            data = zstandard.ZstdCompressor().compress(data)
        else:
            compression_header = JSONDictFieldCompressionAlgorithmEnum.NONE

        return compression_header.value + b":" + b"o:" + data

    def __get__(self, instance, owner):
        """
        We return a custom wrapper over dict which tracks changes to the dictionary and allows us
        to only write the field to the database on update if the field value has changed - very
        important since it means much more efficient partial updates.
        """
        value = super().__get__(instance, owner)

        if isinstance(value, dict) and not isinstance(value, BaseDict):
            value = BaseDict(value, instance, self.name)

        # NOTE: It's important this attribute is set, since only this way mongoengine can determine
        # if the field has chaned or not when determing if the value should be written to the db or
        # not
        if instance:
            instance._data[self.name] = value

        return value


class JSONDictEscapedFieldCompatibilityField(JSONDictField):
    """
    Special version of JSONDictField which takes care of compatibility between old EscapedDictField
    and EscapedDynamicField format and the new one.

    On retrieval, if an old format is detected it's correctly un-serialized and on insertion, we
    always insert data in a new format.
    """

    def to_mongo(self, value):
        if isinstance(value, bytes):
            # Already serialized
            if value[0] == b"{" and self.use_header:
                # Serialized, but doesn't contain header prefix, add it (assume migration from
                # format without a header)
                return "n:o:" + value

            return value

        if not isinstance(value, dict):
            raise ValueError(
                "value argument must be a dictionary (got: %s)" % type(value)
            )

        return self._serialize_field_value(value)

    def to_python(self, value):
        if isinstance(value, dict):
            # Old format which used a native dict with escaped special characters
            # TODO: We can remove that once we assume there is no more old style data in the
            # database and save quite some time.
            value = mongoescape.unescape_chars(value)
            return value

        if isinstance(value, bytes):
            return self.parse_field_value(value)

        return value
