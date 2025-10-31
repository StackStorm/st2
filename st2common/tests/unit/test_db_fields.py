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

import copy
import datetime
import calendar

import mock
import unittest
import orjson
import zstandard

# pytest: make sure monkey_patching happens before importing mongoengine
from st2common.util.monkey_patch import monkey_patch

monkey_patch()

import mongoengine as me

from st2common.fields import ComplexDateTimeField
from st2common.util import date as date_utils
from st2common.models.db import stormbase
from st2common.models.db import MongoDBAccess
from st2common.fields import JSONDictField
from st2common.fields import JSONDictEscapedFieldCompatibilityField
from st2common.fields import JSONDictFieldCompressionAlgorithmEnum
from st2common.fields import JSONDictFieldSerializationFormatEnum

from st2tests import DbTestCase


MOCK_DATA_DICT = {
    "key1": "one",
    "key2": 2,
    "key3": ["a", 1, ["a", "c"], {"d": "e"}, True, None],
    "key4": None,
    "key5": False,
    "key6": {
        "key1": "val1",
        "key2": [2, 3, True],
        "4": False,
        "5": None,
        "6": True,
        "7": 199,
    },
}


# NOTE: Collections of the following two models must be the same for testing purposes
class ModelWithEscapedDynamicFieldDB(stormbase.StormFoundationDB):
    result = stormbase.EscapedDynamicField(default={}, use_header=False)
    counter = me.IntField(default=0)

    meta = {"collection": "model_result_test"}


class ModelWithJSONDictFieldDB(stormbase.StormFoundationDB):
    result = JSONDictField(default={}, use_header=False)
    counter = me.IntField(default=0)

    meta = {"collection": "model_result_test"}


ModelJsonDictFieldAccess = MongoDBAccess(ModelWithJSONDictFieldDB)


class JSONDictFieldTestCase(unittest.TestCase):
    def test_set_to_mongo(self):
        field = JSONDictField(use_header=False)
        result = field.to_mongo({"test": {1, 2}})
        self.assertTrue(isinstance(result, bytes))

    def test_header_set_to_mongo(self):
        field = JSONDictField(use_header=True)
        result = field.to_mongo({"test": {1, 2}})
        self.assertTrue(isinstance(result, bytes))

    def test_to_mongo(self):
        field = JSONDictField(use_header=False)
        result = field.to_mongo(MOCK_DATA_DICT)

        self.assertTrue(isinstance(result, bytes))
        self.assertEqual(result, orjson.dumps(MOCK_DATA_DICT))

    def test_to_python(self):
        field = JSONDictField(use_header=False)

        data = orjson.dumps(MOCK_DATA_DICT)
        result = field.to_python(data)

        self.assertTrue(isinstance(result, dict))
        self.assertEqual(result, MOCK_DATA_DICT)

    def test_roundtrip(self):
        field = JSONDictField(use_header=False)
        result_to_mongo = field.to_mongo(MOCK_DATA_DICT)
        result_to_python = field.to_python(result_to_mongo)

        self.assertEqual(result_to_python, MOCK_DATA_DICT)

        # sets get serialized to a list
        input_dict = {"a": 1, "set": {1, 2, 3, 4, 4, 4, 5, 5}}
        result = {"a": 1, "set": [1, 2, 3, 4, 5]}

        field = JSONDictField(use_header=False)
        result_to_mongo = field.to_mongo(input_dict)
        result_to_python = field.to_python(result_to_mongo)

        self.assertEqual(result_to_python, result)

    def test_parse_field_value(self):
        # 1. Value not provided, should use default one
        field = JSONDictField(use_header=False, default={})
        result = field.parse_field_value(b"")
        self.assertEqual(result, {})

        result = field.parse_field_value(None)
        self.assertEqual(result, {})

        field = JSONDictField(use_header=False, default={"foo": "bar"})
        result = field.parse_field_value(b"")
        self.assertEqual(result, {"foo": "bar"})

        result = field.parse_field_value(None)
        self.assertEqual(result, {"foo": "bar"})

        # Value should be deserialized
        result = field.parse_field_value(b'{"a": "b"}')
        self.assertEqual(result, {"a": "b"})

        # Already a dict
        result = field.parse_field_value({"c": "d"})
        self.assertEqual(result, {"c": "d"})


class JSONDictFieldTestCaseWithHeader(unittest.TestCase):
    def test_to_mongo_no_compression(self):
        field = JSONDictField(use_header=True)

        result = field.to_mongo(MOCK_DATA_DICT)
        self.assertTrue(isinstance(result, bytes))

        split = result.split(b":", 2)
        self.assertEqual(split[0], JSONDictFieldCompressionAlgorithmEnum.NONE.value)
        self.assertEqual(split[1], JSONDictFieldSerializationFormatEnum.ORJSON.value)
        self.assertEqual(orjson.loads(split[2]), MOCK_DATA_DICT)

        parsed_value = field.parse_field_value(result)
        self.assertEqual(parsed_value, MOCK_DATA_DICT)

    def test_to_mongo_zstandard_compression(self):
        field = JSONDictField(use_header=True, compression_algorithm="zstandard")

        result = field.to_mongo(MOCK_DATA_DICT)
        self.assertTrue(isinstance(result, bytes))

        split = result.split(b":", 2)
        self.assertEqual(
            split[0], JSONDictFieldCompressionAlgorithmEnum.ZSTANDARD.value
        )
        self.assertEqual(split[1], JSONDictFieldSerializationFormatEnum.ORJSON.value)
        self.assertEqual(
            orjson.loads(zstandard.ZstdDecompressor().decompress(split[2])),
            MOCK_DATA_DICT,
        )

        parsed_value = field.parse_field_value(result)
        self.assertEqual(parsed_value, MOCK_DATA_DICT)

    def test_to_python_no_compression(self):
        field = JSONDictField(use_header=True)

        serialized_data = field.to_mongo(MOCK_DATA_DICT)

        self.assertTrue(isinstance(serialized_data, bytes))
        split = serialized_data.split(b":", 2)
        self.assertEqual(split[0], JSONDictFieldCompressionAlgorithmEnum.NONE.value)
        self.assertEqual(split[1], JSONDictFieldSerializationFormatEnum.ORJSON.value)

        desserialized_data = field.to_python(serialized_data)
        self.assertEqual(desserialized_data, MOCK_DATA_DICT)

    def test_to_python_zstandard_compression(self):
        field = JSONDictField(use_header=True, compression_algorithm="zstandard")

        serialized_data = field.to_mongo(MOCK_DATA_DICT)
        self.assertTrue(isinstance(serialized_data, bytes))

        split = serialized_data.split(b":", 2)
        self.assertEqual(
            split[0], JSONDictFieldCompressionAlgorithmEnum.ZSTANDARD.value
        )
        self.assertEqual(split[1], JSONDictFieldSerializationFormatEnum.ORJSON.value)

        desserialized_data = field.to_python(serialized_data)
        self.assertEqual(desserialized_data, MOCK_DATA_DICT)


class JSONDictEscapedFieldCompatibilityFieldTestCase(DbTestCase):
    def test_to_mongo(self):
        field = JSONDictEscapedFieldCompatibilityField(use_header=False)

        result_to_mongo_1 = field.to_mongo(MOCK_DATA_DICT)
        self.assertEqual(result_to_mongo_1, orjson.dumps(MOCK_DATA_DICT))

        # Already serialized
        result_to_mongo_2 = field.to_mongo(MOCK_DATA_DICT)
        self.assertEqual(result_to_mongo_2, result_to_mongo_1)

    def test_existing_db_value_is_using_escaped_dict_field_compatibility(self):
        # Verify that backward and forward compatibility is handeld correctly and transparently

        # 1. Insert same model with EscapedDynamicField
        model_db = ModelWithEscapedDynamicFieldDB()
        model_db.result = MOCK_DATA_DICT
        model_db.counter = 0

        inserted_model_db = model_db.save()
        self.assertTrue(inserted_model_db.id)
        self.assertEqual(inserted_model_db.result, MOCK_DATA_DICT)
        self.assertEqual(inserted_model_db.counter, 0)

        # Verify it's stored as EscapedDictField
        pymongo_result = ModelWithEscapedDynamicFieldDB.objects.all().as_pymongo()
        self.assertEqual(len(pymongo_result), 1)
        self.assertEqual(pymongo_result[0]["_id"], inserted_model_db.id)
        self.assertEqual(pymongo_result[0]["result"], MOCK_DATA_DICT)
        self.assertEqual(pymongo_result[0]["counter"], 0)

        # 2. Now read it with JSONDictField and verify it works and gets converted transparently on
        # read
        retrieved_model_db = ModelWithJSONDictFieldDB.objects.get(
            id=inserted_model_db.id
        )
        self.assertEqual(retrieved_model_db.id, inserted_model_db.id)
        self.assertEqual(retrieved_model_db.result, MOCK_DATA_DICT)

        # Verify existing document has been updated
        pymongo_result = ModelWithJSONDictFieldDB.objects.all().as_pymongo()
        self.assertEqual(len(pymongo_result), 1)
        self.assertEqual(pymongo_result[0]["_id"], inserted_model_db.id)
        self.assertEqual(pymongo_result[0]["result"], MOCK_DATA_DICT)
        self.assertEqual(pymongo_result[0]["counter"], 0)

        # 3. Now save it back to the database (should be stored as JSON serialized value)
        updated_data = copy.deepcopy(MOCK_DATA_DICT)
        updated_data["new_key"] = "new value"

        retrieved_model_db.result = updated_data
        retrieved_model_db.counter = 1

        expected_data = copy.deepcopy(MOCK_DATA_DICT)
        expected_data["new_key"] = "new value"

        new_inserted_model_db = retrieved_model_db.save()
        self.assertTrue(new_inserted_model_db.id)
        self.assertEqual(new_inserted_model_db.result, expected_data)
        self.assertEqual(new_inserted_model_db.counter, 1)

        pymongo_result = ModelWithJSONDictFieldDB.objects.all().as_pymongo()
        self.assertEqual(len(pymongo_result), 1)
        self.assertEqual(pymongo_result[0]["_id"], inserted_model_db.id)
        self.assertTrue(isinstance(pymongo_result[0]["result"], bytes))
        self.assertEqual(orjson.loads(pymongo_result[0]["result"]), expected_data)
        self.assertEqual(pymongo_result[0]["counter"], 1)

    def test_field_state_changes_are_correctly_detected_add_or_update_method(self):
        model_db = ModelWithJSONDictFieldDB()
        model_db.result = {"a": 1, "b": 2, "c": [1, 2, 3]}
        expected_result = {"a": 1, "b": 2, "c": [1, 2, 3]}

        model_db = ModelJsonDictFieldAccess.add_or_update(model_db)
        self.assertEqual(model_db.result, expected_result)

        retrieved_model_db = ModelJsonDictFieldAccess.get_by_id(model_db.id)
        self.assertEqual(retrieved_model_db.result, model_db.result)
        self.assertEqual(retrieved_model_db.result, expected_result)

        # 1. Try regular update on the whole attribute level
        model_db.result = {"c": 3, "d": 5}
        expected_result = {"c": 3, "d": 5}

        model_db = ModelJsonDictFieldAccess.add_or_update(model_db)
        self.assertEqual(model_db.result, expected_result)

        retrieved_model_db = ModelJsonDictFieldAccess.get_by_id(model_db.id)
        self.assertEqual(retrieved_model_db.result, model_db.result)
        self.assertEqual(retrieved_model_db.result, expected_result)

        model_db.result = {"f": 6, "g": 7, "c": [9, 8, 7]}
        expected_result = {"f": 6, "g": 7, "c": [9, 8, 7]}
        model_db = ModelJsonDictFieldAccess.add_or_update(model_db)
        self.assertEqual(model_db.result, expected_result)

        retrieved_model_db = ModelJsonDictFieldAccess.get_by_id(model_db.id)
        self.assertEqual(retrieved_model_db.result, model_db.result)
        self.assertEqual(retrieved_model_db.result, expected_result)

        # 2. Try updating a single field in the dict - this would not be detected by the default
        # field change detection logic of mongoengine for our special field type
        model_db = retrieved_model_db
        model_db.result["f"] = 1000
        model_db.result["h"] = 100
        expected_result = {"f": 1000, "g": 7, "h": 100, "c": [9, 8, 7]}

        model_db = ModelJsonDictFieldAccess.add_or_update(model_db)
        self.assertEqual(model_db.result, expected_result)

        retrieved_model_db = ModelJsonDictFieldAccess.get_by_id(model_db.id)
        self.assertEqual(retrieved_model_db.result, model_db.result)
        self.assertEqual(retrieved_model_db.result, expected_result)

        # Try again
        model_db.result["u"] = 102
        expected_result = {"f": 1000, "g": 7, "h": 100, "u": 102, "c": [9, 8, 7]}

        model_db = ModelJsonDictFieldAccess.add_or_update(model_db)
        self.assertEqual(model_db.result, expected_result)

        retrieved_model_db = ModelJsonDictFieldAccess.get_by_id(model_db.id)
        self.assertEqual(retrieved_model_db.result, model_db.result)
        self.assertEqual(retrieved_model_db.result, expected_result)

        # Verify nested list items state changes are also tracked correctly
        model_db.result["c"].append(6)
        expected_result = {"f": 1000, "g": 7, "h": 100, "u": 102, "c": [9, 8, 7, 6]}

        model_db = ModelJsonDictFieldAccess.add_or_update(model_db)
        self.assertEqual(model_db.result, expected_result)

        retrieved_model_db = ModelJsonDictFieldAccess.get_by_id(model_db.id)
        self.assertEqual(retrieved_model_db.result, model_db.result)
        self.assertEqual(retrieved_model_db.result, expected_result)

        model_db.result["c"][0] = 100
        expected_result = {"f": 1000, "g": 7, "h": 100, "u": 102, "c": [100, 8, 7, 6]}

        model_db = ModelJsonDictFieldAccess.add_or_update(model_db)
        self.assertEqual(model_db.result, expected_result)

        retrieved_model_db = ModelJsonDictFieldAccess.get_by_id(model_db.id)
        self.assertEqual(retrieved_model_db.result, model_db.result)
        self.assertEqual(retrieved_model_db.result, expected_result)

        # Verify nested dict item dict changes
        model_db = ModelWithJSONDictFieldDB()
        model_db.result = {"a": 1, "b": 2, "c": {"a1": {"b1": "c"}}}
        expected_result = {"a": 1, "b": 2, "c": {"a1": {"b1": "c"}}}

        model_db = ModelJsonDictFieldAccess.add_or_update(model_db)
        self.assertEqual(model_db.result, expected_result)

        retrieved_model_db = ModelJsonDictFieldAccess.get_by_id(model_db.id)
        self.assertEqual(retrieved_model_db.result, model_db.result)
        self.assertEqual(retrieved_model_db.result, expected_result)

        model_db.result["c"]["a1"]["b1"] = "updated"
        expected_result = {"a": 1, "b": 2, "c": {"a1": {"b1": "updated"}}}

        model_db = ModelJsonDictFieldAccess.add_or_update(model_db)
        self.assertEqual(model_db.result, expected_result)

        retrieved_model_db = ModelJsonDictFieldAccess.get_by_id(model_db.id)
        self.assertEqual(retrieved_model_db.result, model_db.result)
        self.assertEqual(retrieved_model_db.result, expected_result)

        # And again with different approach (we set field on the original model, not one returned
        # by add_or_update())
        model_0_db = ModelWithJSONDictFieldDB()
        model_0_db.result = {"f": "f", "g": "g", "c": [9, 8, 7]}
        expected_result = {"f": "f", "g": "g", "c": [9, 8, 7]}

        inserted_model_db = ModelJsonDictFieldAccess.add_or_update(model_0_db)
        self.assertEqual(inserted_model_db.result, model_0_db.result)
        self.assertEqual(inserted_model_db.result, expected_result)

        retrieved_model_db = ModelJsonDictFieldAccess.get_by_id(model_0_db.id)
        self.assertEqual(retrieved_model_db.result, model_0_db.result)
        self.assertEqual(retrieved_model_db.result, expected_result)

        model_0_db["result"]["f"] = "updated!"
        expected_result = {"f": "updated!", "g": "g", "c": [9, 8, 7]}

        inserted_model_db = ModelJsonDictFieldAccess.add_or_update(model_0_db)
        self.assertEqual(inserted_model_db.result, model_0_db.result)
        self.assertEqual(inserted_model_db.result, expected_result)

        retrieved_model_db = ModelJsonDictFieldAccess.get_by_id(model_0_db.id)
        self.assertEqual(retrieved_model_db.result, model_0_db.result)
        self.assertEqual(retrieved_model_db.result, expected_result)

        # Verify nested list items state changes are also tracked correctly
        model_0_db.result["c"].append(6)
        expected_result = {"f": "updated!", "g": "g", "c": [9, 8, 7, 6]}

        inserted_model_db = ModelJsonDictFieldAccess.add_or_update(model_0_db)
        self.assertEqual(inserted_model_db.result, model_0_db.result)
        self.assertEqual(inserted_model_db.result, expected_result)

        retrieved_model_db = ModelJsonDictFieldAccess.get_by_id(model_0_db.id)
        self.assertEqual(retrieved_model_db.result, model_0_db.result)
        self.assertEqual(retrieved_model_db.result, expected_result)

        model_0_db.result["c"][1] = 100
        expected_result = {"f": "updated!", "g": "g", "c": [9, 100, 7, 6]}

        inserted_model_db = ModelJsonDictFieldAccess.add_or_update(model_0_db)
        self.assertEqual(inserted_model_db.result, model_0_db.result)
        self.assertEqual(inserted_model_db.result, expected_result)

        retrieved_model_db = ModelJsonDictFieldAccess.get_by_id(model_0_db.id)
        self.assertEqual(inserted_model_db.result, model_0_db.result)
        self.assertEqual(retrieved_model_db.result, expected_result)

    def test_field_state_changes_are_correctly_detected_save_method(self):
        model_db = ModelWithJSONDictFieldDB()
        model_db.result = {"a": 1, "b": 2, "c": ["a", "b", 100]}
        expected_result = {"a": 1, "b": 2, "c": ["a", "b", 100]}

        model_db = model_db.save()
        self.assertEqual(model_db.result, expected_result)

        retrieved_model_db = ModelJsonDictFieldAccess.get_by_id(model_db.id)
        self.assertEqual(retrieved_model_db.result, model_db.result)
        self.assertEqual(retrieved_model_db.result, expected_result)

        # 1. Try regular update on the whole attribute level
        model_db.result = {"h": 3, "d": 5, "c": ["a", "b", 101]}
        expected_result = {"h": 3, "d": 5, "c": ["a", "b", 101]}
        model_db = model_db.save()

        retrieved_model_db = ModelJsonDictFieldAccess.get_by_id(model_db.id)
        self.assertEqual(retrieved_model_db.result, model_db.result)
        self.assertEqual(retrieved_model_db.result, expected_result)

        model_db.result = {"f": 6, "g": 7, "c": ["a", "b", 102]}
        expected_result = {"f": 6, "g": 7, "c": ["a", "b", 102]}
        model_db = model_db.save()
        self.assertEqual(model_db.result, expected_result)

        retrieved_model_db = ModelJsonDictFieldAccess.get_by_id(model_db.id)
        self.assertEqual(retrieved_model_db.result, model_db.result)
        self.assertEqual(retrieved_model_db.result, expected_result)

        # 2. Try updating a single field in the dict - this would not be detected by the default
        # field change detection logic of mongoengine for our special field type
        model_db = retrieved_model_db
        model_db.result["f"] = 1000
        model_db.result["d"] = 100
        expected_result = {"f": 1000, "g": 7, "d": 100, "c": ["a", "b", 102]}
        model_db = model_db.save()
        self.assertEqual(model_db.result, expected_result)

        retrieved_model_db = ModelJsonDictFieldAccess.get_by_id(model_db.id)
        self.assertEqual(retrieved_model_db.result, model_db.result)
        self.assertEqual(retrieved_model_db.result, expected_result)

        # Try again
        model_db.result["u"] = 102
        expected_result = {"f": 1000, "g": 7, "d": 100, "u": 102, "c": ["a", "b", 102]}
        model_db = model_db.save()
        self.assertEqual(model_db.result, expected_result)

        retrieved_model_db = ModelJsonDictFieldAccess.get_by_id(model_db.id)
        self.assertEqual(retrieved_model_db.result, model_db.result)
        self.assertEqual(retrieved_model_db.result, expected_result)

        # Verify nested list items state changes are also tracked correctly
        model_db.result["c"][2] += 10
        expected_result = {"f": 1000, "g": 7, "d": 100, "u": 102, "c": ["a", "b", 112]}
        model_db = model_db.save()
        self.assertEqual(model_db.result, expected_result)

        retrieved_model_db = ModelJsonDictFieldAccess.get_by_id(model_db.id)
        self.assertEqual(retrieved_model_db.result, model_db.result)
        self.assertEqual(retrieved_model_db.result, expected_result)

        # And again with different approach (we set field on the original model, not one returned
        # by add_or_update())
        model_0_db = ModelWithJSONDictFieldDB()
        model_0_db.result = {"f": "f", "g": "g"}
        expected_result = {"f": "f", "g": "g"}

        inserted_model_db = model_0_db.save()
        self.assertEqual(inserted_model_db.result, model_0_db.result)
        self.assertEqual(inserted_model_db.result, expected_result)

        retrieved_model_db = ModelJsonDictFieldAccess.get_by_id(model_0_db.id)
        self.assertEqual(retrieved_model_db.result, model_0_db.result)
        self.assertEqual(retrieved_model_db.result, expected_result)

        model_0_db["result"]["f"] = "updated!"
        expected_result = {"f": "updated!", "g": "g"}

        inserted_model_db = model_0_db.save()
        self.assertEqual(inserted_model_db.result, model_0_db.result)
        self.assertEqual(inserted_model_db.result, expected_result)

        retrieved_model_db = ModelJsonDictFieldAccess.get_by_id(model_0_db.id)
        self.assertEqual(retrieved_model_db.result, model_0_db.result)
        self.assertEqual(retrieved_model_db.result, expected_result)


class ComplexDateTimeFieldTestCase(unittest.TestCase):
    def test_what_comes_in_goes_out(self):
        field = ComplexDateTimeField()

        date = date_utils.get_datetime_utc_now()
        us = field._datetime_to_microseconds_since_epoch(date)
        result = field._microseconds_since_epoch_to_datetime(us)
        self.assertEqual(date, result)

    def test_round_trip_conversion(self):
        datetime_values = [
            datetime.datetime(2015, 1, 1, 15, 0, 0).replace(microsecond=500),
            datetime.datetime(2015, 1, 1, 15, 0, 0).replace(microsecond=0),
            datetime.datetime(2015, 1, 1, 15, 0, 0).replace(microsecond=999999),
        ]
        datetime_values = [
            date_utils.add_utc_tz(datetime_values[0]),
            date_utils.add_utc_tz(datetime_values[1]),
            date_utils.add_utc_tz(datetime_values[2]),
        ]
        microsecond_values = []

        # Calculate microsecond values
        for value in datetime_values:
            seconds = calendar.timegm(value.timetuple())
            microseconds_reminder = value.time().microsecond
            result = int(seconds * 1000000) + microseconds_reminder
            microsecond_values.append(result)

        field = ComplexDateTimeField()
        # datetime to us
        for index, value in enumerate(datetime_values):
            actual_value = field._datetime_to_microseconds_since_epoch(value=value)
            expected_value = microsecond_values[index]
            expected_microseconds = value.time().microsecond

            self.assertEqual(actual_value, expected_value)
            self.assertTrue(str(actual_value).endswith(str(expected_microseconds)))

        # us to datetime
        for index, value in enumerate(microsecond_values):
            actual_value = field._microseconds_since_epoch_to_datetime(data=value)
            expected_value = datetime_values[index]
            self.assertEqual(actual_value, expected_value)

    @mock.patch("st2common.fields.LongField.__get__")
    def test_get_(self, mock_get):
        field = ComplexDateTimeField()

        # No value set
        mock_get.return_value = None
        self.assertEqual(field.__get__(instance=None, owner=None), None)

        # Already a datetime
        mock_get.return_value = date_utils.get_datetime_utc_now()
        self.assertEqual(
            field.__get__(instance=None, owner=None), mock_get.return_value
        )

        # Microseconds
        dt = datetime.datetime(2015, 1, 1, 15, 0, 0).replace(microsecond=500)
        dt = date_utils.add_utc_tz(dt)
        us = field._datetime_to_microseconds_since_epoch(value=dt)
        mock_get.return_value = us
        self.assertEqual(field.__get__(instance=None, owner=None), dt)
