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

from unittest2 import TestCase
from jsonschema.exceptions import ValidationError

from st2common.util import schema as util_schema

TEST_SCHEMA_1 = {
    'additionalProperties': False,
    'title': 'foo',
    'description': 'Foo.',
    'type': 'object',
    'properties': {
        'arg_required_no_default': {
            'description': 'Foo',
            'required': True,
            'type': 'string'
        },
        'arg_optional_no_type': {
            'description': 'Bar'
        },
        'arg_optional_multi_type': {
            'description': 'Mirror mirror',
            'type': ['string', 'boolean', 'number']
        },
        'arg_optional_multi_type_none': {
            'description': 'Mirror mirror on the wall',
            'type': ['string', 'boolean', 'number', 'null']
        },
        'arg_optional_type_array': {
            'description': 'Who''s the fairest?',
            'type': 'array'
        },
        'arg_optional_type_object': {
            'description': 'Who''s the fairest of them?',
            'type': 'object'
        },
        'arg_optional_multi_collection_type': {
            'description': 'Who''s the fairest of them all?',
            'type': ['array', 'object']
        }
    }
}

TEST_SCHEMA_2 = {
    'additionalProperties': False,
    'title': 'foo',
    'description': 'Foo.',
    'type': 'object',
    'properties': {
        'arg_required_default': {
            'default': 'date',
            'description': 'Foo',
            'required': True,
            'type': 'string'
        }
    }
}

TEST_SCHEMA_3 = {
    'additionalProperties': False,
    'title': 'foo',
    'description': 'Foo.',
    'type': 'object',
    'properties': {
        'arg_optional_default': {
            'default': 'bar',
            'description': 'Foo',
            'type': 'string'
        },
        'arg_optional_default_none': {
            'default': None,
            'description': 'Foo',
            'type': 'string'
        },
        'arg_optional_no_default': {
            'description': 'Foo',
            'type': 'string'
        }
    }
}

TEST_SCHEMA_4 = {
    'additionalProperties': False,
    'title': 'foo',
    'description': 'Foo.',
    'type': 'object',
    'properties': {
        'arg_optional_default': {
            'default': 'bar',
            'description': 'Foo',
            'anyOf': [
                {'type': 'string'},
                {'type': 'boolean'}
            ]
        },
        'arg_optional_default_none': {
            'default': None,
            'description': 'Foo',
            'anyOf': [
                {'type': 'string'},
                {'type': 'boolean'}
            ]
        },
        'arg_optional_no_default': {
            'description': 'Foo',
            'anyOf': [
                {'type': 'string'},
                {'type': 'boolean'}
            ]
        },
        'arg_optional_no_default_anyof_none': {
            'description': 'Foo',
            'anyOf': [
                {'type': 'string'},
                {'type': 'boolean'},
                {'type': 'null'}
            ]
        }
    }
}

TEST_SCHEMA_5 = {
    'additionalProperties': False,
    'title': 'foo',
    'description': 'Foo.',
    'type': 'object',
    'properties': {
        'arg_optional_default': {
            'default': 'bar',
            'description': 'Foo',
            'oneOf': [
                {'type': 'string'},
                {'type': 'boolean'}
            ]
        },
        'arg_optional_default_none': {
            'default': None,
            'description': 'Foo',
            'oneOf': [
                {'type': 'string'},
                {'type': 'boolean'}
            ]
        },
        'arg_optional_no_default': {
            'description': 'Foo',
            'oneOf': [
                {'type': 'string'},
                {'type': 'boolean'}
            ]
        },
        'arg_optional_no_default_oneof_none': {
            'description': 'Foo',
            'oneOf': [
                {'type': 'string'},
                {'type': 'boolean'},
                {'type': 'null'}
            ]
        }
    }
}


class JSONSchemaTestCase(TestCase):
    def test_use_default_value(self):
        # No default, no value provided, should fail
        instance = {}
        validator = util_schema.get_validator()

        expected_msg = '\'arg_required_no_default\' is a required property'
        self.assertRaisesRegexp(ValidationError, expected_msg, util_schema.validate,
                                instance=instance, schema=TEST_SCHEMA_1, cls=validator,
                                use_default=True)

        # No default, value provided
        instance = {'arg_required_no_default': 'foo'}
        util_schema.validate(instance=instance, schema=TEST_SCHEMA_1, cls=validator,
                             use_default=True)

        # default value provided, no value, should pass
        instance = {}
        validator = util_schema.get_validator()
        util_schema.validate(instance=instance, schema=TEST_SCHEMA_2, cls=validator,
                             use_default=True)

        # default value provided, value provided, should pass
        instance = {'arg_required_default': 'foo'}
        validator = util_schema.get_validator()
        util_schema.validate(instance=instance, schema=TEST_SCHEMA_2, cls=validator,
                             use_default=True)

    def test_allow_default_none(self):
        # Let validator take care of default
        validator = util_schema.get_validator()
        util_schema.validate(instance=dict(), schema=TEST_SCHEMA_3, cls=validator,
                             use_default=True, allow_default_none=True)

    def test_allow_default_explicit_none(self):
        # Explicitly pass None to arguments
        instance = {
            'arg_optional_default': None,
            'arg_optional_default_none': None,
            'arg_optional_no_default': None
        }

        validator = util_schema.get_validator()
        util_schema.validate(instance=instance, schema=TEST_SCHEMA_3, cls=validator,
                             use_default=True, allow_default_none=True)

    def test_anyof_type_allow_default_none(self):
        # Let validator take care of default
        validator = util_schema.get_validator()
        util_schema.validate(instance=dict(), schema=TEST_SCHEMA_4, cls=validator,
                             use_default=True, allow_default_none=True)

    def test_anyof_allow_default_explicit_none(self):
        # Explicitly pass None to arguments
        instance = {
            'arg_optional_default': None,
            'arg_optional_default_none': None,
            'arg_optional_no_default': None,
            'arg_optional_no_default_anyof_none': None
        }

        validator = util_schema.get_validator()
        util_schema.validate(instance=instance, schema=TEST_SCHEMA_4, cls=validator,
                             use_default=True, allow_default_none=True)

    def test_oneof_type_allow_default_none(self):
        # Let validator take care of default
        validator = util_schema.get_validator()
        util_schema.validate(instance=dict(), schema=TEST_SCHEMA_5, cls=validator,
                             use_default=True, allow_default_none=True)

    def test_oneof_allow_default_explicit_none(self):
        # Explicitly pass None to arguments
        instance = {
            'arg_optional_default': None,
            'arg_optional_default_none': None,
            'arg_optional_no_default': None,
            'arg_optional_no_default_oneof_none': None
        }

        validator = util_schema.get_validator()
        util_schema.validate(instance=instance, schema=TEST_SCHEMA_5, cls=validator,
                             use_default=True, allow_default_none=True)

    def test_is_property_type_single(self):
        typed_property = TEST_SCHEMA_1['properties']['arg_required_no_default']
        self.assertTrue(util_schema.is_property_type_single(typed_property))

        untyped_property = TEST_SCHEMA_1['properties']['arg_optional_no_type']
        self.assertTrue(util_schema.is_property_type_single(untyped_property))

        multi_typed_property = TEST_SCHEMA_1['properties']['arg_optional_multi_type']
        self.assertFalse(util_schema.is_property_type_single(multi_typed_property))

        anyof_property = TEST_SCHEMA_4['properties']['arg_optional_default']
        self.assertFalse(util_schema.is_property_type_single(anyof_property))

        oneof_property = TEST_SCHEMA_5['properties']['arg_optional_default']
        self.assertFalse(util_schema.is_property_type_single(oneof_property))

    def test_is_property_type_anyof(self):
        anyof_property = TEST_SCHEMA_4['properties']['arg_optional_default']
        self.assertTrue(util_schema.is_property_type_anyof(anyof_property))

        typed_property = TEST_SCHEMA_1['properties']['arg_required_no_default']
        self.assertFalse(util_schema.is_property_type_anyof(typed_property))

        untyped_property = TEST_SCHEMA_1['properties']['arg_optional_no_type']
        self.assertFalse(util_schema.is_property_type_anyof(untyped_property))

        multi_typed_property = TEST_SCHEMA_1['properties']['arg_optional_multi_type']
        self.assertFalse(util_schema.is_property_type_anyof(multi_typed_property))

        oneof_property = TEST_SCHEMA_5['properties']['arg_optional_default']
        self.assertFalse(util_schema.is_property_type_anyof(oneof_property))

    def test_is_property_type_oneof(self):
        oneof_property = TEST_SCHEMA_5['properties']['arg_optional_default']
        self.assertTrue(util_schema.is_property_type_oneof(oneof_property))

        typed_property = TEST_SCHEMA_1['properties']['arg_required_no_default']
        self.assertFalse(util_schema.is_property_type_oneof(typed_property))

        untyped_property = TEST_SCHEMA_1['properties']['arg_optional_no_type']
        self.assertFalse(util_schema.is_property_type_oneof(untyped_property))

        multi_typed_property = TEST_SCHEMA_1['properties']['arg_optional_multi_type']
        self.assertFalse(util_schema.is_property_type_oneof(multi_typed_property))

        anyof_property = TEST_SCHEMA_4['properties']['arg_optional_default']
        self.assertFalse(util_schema.is_property_type_oneof(anyof_property))

    def test_is_property_type_list(self):
        multi_typed_property = TEST_SCHEMA_1['properties']['arg_optional_multi_type']
        self.assertTrue(util_schema.is_property_type_list(multi_typed_property))

        typed_property = TEST_SCHEMA_1['properties']['arg_required_no_default']
        self.assertFalse(util_schema.is_property_type_list(typed_property))

        untyped_property = TEST_SCHEMA_1['properties']['arg_optional_no_type']
        self.assertFalse(util_schema.is_property_type_list(untyped_property))

        anyof_property = TEST_SCHEMA_4['properties']['arg_optional_default']
        self.assertFalse(util_schema.is_property_type_list(anyof_property))

        oneof_property = TEST_SCHEMA_5['properties']['arg_optional_default']
        self.assertFalse(util_schema.is_property_type_list(oneof_property))

    def test_is_property_nullable(self):
        multi_typed_prop_nullable = TEST_SCHEMA_1['properties']['arg_optional_multi_type_none']
        self.assertTrue(util_schema.is_property_nullable(multi_typed_prop_nullable.get('type')))

        anyof_property_nullable = TEST_SCHEMA_4['properties']['arg_optional_no_default_anyof_none']
        self.assertTrue(util_schema.is_property_nullable(anyof_property_nullable.get('anyOf')))

        oneof_property_nullable = TEST_SCHEMA_5['properties']['arg_optional_no_default_oneof_none']
        self.assertTrue(util_schema.is_property_nullable(oneof_property_nullable.get('oneOf')))

        typed_property = TEST_SCHEMA_1['properties']['arg_required_no_default']
        self.assertFalse(util_schema.is_property_nullable(typed_property))

        multi_typed_property = TEST_SCHEMA_1['properties']['arg_optional_multi_type']
        self.assertFalse(util_schema.is_property_nullable(multi_typed_property.get('type')))

        anyof_property = TEST_SCHEMA_4['properties']['arg_optional_no_default']
        self.assertFalse(util_schema.is_property_nullable(anyof_property.get('anyOf')))

        oneof_property = TEST_SCHEMA_5['properties']['arg_optional_no_default']
        self.assertFalse(util_schema.is_property_nullable(oneof_property.get('oneOf')))

    def test_is_attribute_type_array(self):
        multi_coll_typed_prop = TEST_SCHEMA_1['properties']['arg_optional_multi_collection_type']
        self.assertTrue(util_schema.is_attribute_type_array(multi_coll_typed_prop.get('type')))

        array_type_property = TEST_SCHEMA_1['properties']['arg_optional_type_array']
        self.assertTrue(util_schema.is_attribute_type_array(array_type_property.get('type')))

        multi_non_coll_prop = TEST_SCHEMA_1['properties']['arg_optional_multi_type']
        self.assertFalse(util_schema.is_attribute_type_array(multi_non_coll_prop.get('type')))

        object_type_property = TEST_SCHEMA_1['properties']['arg_optional_type_object']
        self.assertFalse(util_schema.is_attribute_type_array(object_type_property.get('type')))

    def test_is_attribute_type_object(self):
        multi_coll_typed_prop = TEST_SCHEMA_1['properties']['arg_optional_multi_collection_type']
        self.assertTrue(util_schema.is_attribute_type_object(multi_coll_typed_prop.get('type')))

        object_type_property = TEST_SCHEMA_1['properties']['arg_optional_type_object']
        self.assertTrue(util_schema.is_attribute_type_object(object_type_property.get('type')))

        multi_non_coll_prop = TEST_SCHEMA_1['properties']['arg_optional_multi_type']
        self.assertFalse(util_schema.is_attribute_type_object(multi_non_coll_prop.get('type')))

        array_type_property = TEST_SCHEMA_1['properties']['arg_optional_type_array']
        self.assertFalse(util_schema.is_attribute_type_object(array_type_property.get('type')))
