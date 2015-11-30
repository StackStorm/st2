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

import os
import copy

import six
import jsonschema
from jsonschema import _validators
from jsonschema.validators import create

from st2common.util import jsonify

__all__ = [
    'get_validator',
    'get_draft_schema',
    'get_action_parameters_schema',
    'get_schema_for_action_parameters',
    'get_schema_for_resource_parameters',
    'validate'
]

# https://github.com/json-schema/json-schema/blob/master/draft-04/schema
# The source material is licensed under the AFL or BSD license.
# Both draft 4 and custom schema has additionalProperties set to false by default.
# The custom schema differs from draft 4 with the extension of position, immutable,
# and draft 3 version of required.
PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)))
SCHEMAS = {
    'draft4': jsonify.load_file(os.path.join(PATH, 'draft4.json')),
    'custom': jsonify.load_file(os.path.join(PATH, 'custom.json')),

    # Custom schema for action params which doesn't allow parameter "type" attribute to be array
    'action_params': jsonify.load_file(os.path.join(PATH, 'action_params.json'))
}

SCHEMA_ANY_TYPE = {
    "anyOf": [
        {"type": "array"},
        {"type": "boolean"},
        {"type": "integer"},
        {"type": "number"},
        {"type": "object"},
        {"type": "string"}
    ]
}


def get_draft_schema(version='custom', additional_properties=False):
    schema = copy.deepcopy(SCHEMAS[version])
    if additional_properties and 'additionalProperties' in schema:
        del schema['additionalProperties']
    return schema


def get_action_parameters_schema(additional_properties=False):
    """
    Return a generic schema which is used for validating action parameters definition.
    """
    return get_draft_schema(version='action_params', additional_properties=additional_properties)


CustomValidator = create(
    meta_schema=get_draft_schema(version='custom', additional_properties=True),
    validators={
        u"$ref": _validators.ref,
        u"additionalItems": _validators.additionalItems,
        u"additionalProperties": _validators.additionalProperties,
        u"allOf": _validators.allOf_draft4,
        u"anyOf": _validators.anyOf_draft4,
        u"dependencies": _validators.dependencies,
        u"enum": _validators.enum,
        u"format": _validators.format,
        u"items": _validators.items,
        u"maxItems": _validators.maxItems,
        u"maxLength": _validators.maxLength,
        u"maxProperties": _validators.maxProperties_draft4,
        u"maximum": _validators.maximum,
        u"minItems": _validators.minItems,
        u"minLength": _validators.minLength,
        u"minProperties": _validators.minProperties_draft4,
        u"minimum": _validators.minimum,
        u"multipleOf": _validators.multipleOf,
        u"not": _validators.not_draft4,
        u"oneOf": _validators.oneOf_draft4,
        u"pattern": _validators.pattern,
        u"patternProperties": _validators.patternProperties,
        u"properties": _validators.properties_draft3,
        u"type": _validators.type_draft4,
        u"uniqueItems": _validators.uniqueItems,
    },
    version="custom_validator",
)


def assign_default_values(instance, schema):
    """
    Assign default values on the provided instance based on the schema default specification.
    """
    instance = copy.deepcopy(instance)
    instance_is_dict = isinstance(instance, dict)
    instance_is_array = isinstance(instance, list)

    if not instance_is_dict and not instance_is_array:
        return instance

    properties = schema.get('properties', {})
    for property_name, property_data in six.iteritems(properties):
        has_default_value = 'default' in property_data
        default_value = property_data.get('default', None)

        # Assign default value on the instance so the validation doesn't fail if requires is true
        # but the value is not provided
        if has_default_value:
            if instance_is_dict and instance.get(property_name, None) is None:
                instance[property_name] = default_value
            elif instance_is_array:
                for index, _ in enumerate(instance):
                    if instance[index].get(property_name, None) is None:
                        instance[index][property_name] = default_value

        # Support for nested properties (array and object)
        attribute_type = property_data.get('type', None)
        schema_items = property_data.get('items', {})

        # Array
        if attribute_type == 'array' and schema_items and schema_items.get('properties', {}):
            array_instance = instance.get(property_name, None)
            array_schema = schema['properties'][property_name]['items']

            if array_instance is not None:
                # Note: We don't perform subschema assignment if no value is provided
                instance[property_name] = assign_default_values(instance=array_instance,
                                                                schema=array_schema)

        # Object
        if attribute_type == 'object' and property_data.get('properties', {}):
            object_instance = instance.get(property_name, None)
            object_schema = schema['properties'][property_name]

            if object_instance is not None:
                # Note: We don't perform subschema assignment if no value is provided
                instance[property_name] = assign_default_values(instance=object_instance,
                                                                schema=object_schema)

    return instance


def modify_schema_allow_default_none(schema):
    """
    Manipulate the provided schema so None is also an allowed value for each attribute which
    defines a default value of None.
    """
    schema = copy.deepcopy(schema)

    properties = schema.get('properties', {})
    for property_name, property_data in six.iteritems(properties):
        has_default_value = 'default' in property_data
        default_value = property_data.get('default', None)

        if has_default_value and default_value is None:
            # Allow "None" to be also used as a valid attribute value
            property_type = schema['properties'][property_name]['type']

            if isinstance(property_type, list) and 'null' not in property_type:
                schema['properties'][property_name]['type'].append('null')
            elif isinstance(property_type, six.string_types) and 'null' not in property_type:
                schema['properties'][property_name]['type'] = [property_type, 'null']

        # Support for nested properties (array and object)
        attribute_type = property_data.get('type', None)
        schema_items = property_data.get('items', {})

        # Array
        if attribute_type == 'array' and schema_items and schema_items.get('properties', {}):
            array_schema = schema_items
            array_schema = modify_schema_allow_default_none(schema=array_schema)
            schema['properties'][property_name]['items'] = array_schema

        # Object
        if attribute_type == 'object' and property_data.get('properties', {}):
            object_schema = property_data
            object_schema = modify_schema_allow_default_none(schema=object_schema)
            schema['properties'][property_name] = object_schema

    return schema


def validate(instance, schema, cls=None, use_default=True, allow_default_none=False, *args,
             **kwargs):
    """
    Custom validate function which supports default arguments combined with the "required"
    property.

    Note: This function returns cleaned instance with default values assigned.

    :param use_default: True to support the use of the optional "default" property.
    :type use_default: ``bool``
    """
    instance = copy.deepcopy(instance)
    schema_type = schema.get('type', None)
    instance_is_dict = isinstance(instance, dict)

    if use_default and allow_default_none:
        schema = modify_schema_allow_default_none(schema=schema)

    if use_default and schema_type == 'object' and instance_is_dict:
        instance = assign_default_values(instance=instance, schema=schema)

    # pylint: disable=assignment-from-no-return
    jsonschema.validate(instance=instance, schema=schema, cls=cls, *args, **kwargs)
    return instance


VALIDATORS = {
    'draft4': jsonschema.Draft4Validator,
    'custom': CustomValidator
}


def get_validator(version='custom'):
    validator = VALIDATORS[version]
    return validator


def get_schema_for_action_parameters(action_db):
    """
    Dynamically construct JSON schema for the provided action from the parameters metadata.

    Note: This schema is used to validate parameters which are passed to the action.
    """
    from st2common.util.action_db import get_runnertype_by_name
    runner_type = get_runnertype_by_name(action_db.runner_type['name'])

    parameters_schema = {}
    parameters_schema.update(runner_type.runner_parameters)
    parameters_schema.update(action_db.parameters)

    schema = get_schema_for_resource_parameters(parameters_schema=parameters_schema)

    if parameters_schema:
        schema['title'] = action_db.name
        if action_db.description:
            schema['description'] = action_db.description

    return schema


def get_schema_for_resource_parameters(parameters_schema):
    """
    Dynamically construct JSON schema for the provided resource from the parameters metadata.
    """
    def normalize(x):
        return {k: v if v else SCHEMA_ANY_TYPE for k, v in six.iteritems(x)}

    schema = {}
    properties = {}
    properties.update(normalize(parameters_schema))
    if properties:
        schema['type'] = 'object'
        schema['properties'] = properties
        schema['additionalProperties'] = False

    return schema
