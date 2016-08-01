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

from st2common.exceptions.action import InvalidActionParameterException
from st2common.util import jsonify
from st2common.util.misc import deep_update

__all__ = [
    'get_validator',
    'get_draft_schema',
    'get_action_parameters_schema',
    'get_schema_for_action_parameters',
    'get_schema_for_resource_parameters',
    'is_property_type_single',
    'is_property_type_list',
    'is_property_type_anyof',
    'is_property_type_oneof',
    'is_property_nullable',
    'is_attribute_type_array',
    'is_attribute_type_object',
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

RUNNER_PARAM_OVERRIDABLE_ATTRS = [
    'default',
    'description',
    'enum',
    'immutable',
    'required'
]


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


def is_property_type_single(property_schema):
    return (isinstance(property_schema, dict) and
            'anyOf' not in property_schema.keys() and
            'oneOf' not in property_schema.keys() and
            not isinstance(property_schema.get('type', 'string'), list))


def is_property_type_list(property_schema):
    return (isinstance(property_schema, dict) and
            isinstance(property_schema.get('type', 'string'), list))


def is_property_type_anyof(property_schema):
    return isinstance(property_schema, dict) and 'anyOf' in property_schema.keys()


def is_property_type_oneof(property_schema):
    return isinstance(property_schema, dict) and 'oneOf' in property_schema.keys()


def is_property_nullable(property_type_schema):
    # For anyOf and oneOf, the property_schema is a list of types.
    if isinstance(property_type_schema, list):
        return len([t for t in property_type_schema
                    if ((isinstance(t, six.string_types) and t == 'null') or
                        (isinstance(t, dict) and t.get('type', 'string') == 'null'))]) > 0

    return (isinstance(property_type_schema, dict) and
            property_type_schema.get('type', 'string') == 'null')


def is_attribute_type_array(attribute_type):
    return (attribute_type == 'array' or
            (isinstance(attribute_type, list) and 'array' in attribute_type))


def is_attribute_type_object(attribute_type):
    return (attribute_type == 'object' or
            (isinstance(attribute_type, list) and 'object' in attribute_type))


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
        if (is_attribute_type_array(attribute_type) and
                schema_items and schema_items.get('properties', {})):
            array_instance = instance.get(property_name, None)
            array_schema = schema['properties'][property_name]['items']

            if array_instance is not None:
                # Note: We don't perform subschema assignment if no value is provided
                instance[property_name] = assign_default_values(instance=array_instance,
                                                                schema=array_schema)

        # Object
        if is_attribute_type_object(attribute_type) and property_data.get('properties', {}):
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
        is_optional = not property_data.get('required', False)
        has_default_value = 'default' in property_data
        default_value = property_data.get('default', None)
        property_schema = schema['properties'][property_name]

        if (has_default_value or is_optional) and default_value is None:
            # If property is anyOf and oneOf then it has to be process differently.
            if (is_property_type_anyof(property_schema) and
                    not is_property_nullable(property_schema['anyOf'])):
                property_schema['anyOf'].append({'type': 'null'})
            elif (is_property_type_oneof(property_schema) and
                    not is_property_nullable(property_schema['oneOf'])):
                property_schema['oneOf'].append({'type': 'null'})
            elif (is_property_type_list(property_schema) and
                    not is_property_nullable(property_schema.get('type'))):
                property_schema['type'].append('null')
            elif (is_property_type_single(property_schema) and
                    not is_property_nullable(property_schema.get('type'))):
                property_schema['type'] = [property_schema.get('type', 'string'), 'null']

        # Support for nested properties (array and object)
        attribute_type = property_data.get('type', None)
        schema_items = property_data.get('items', {})

        # Array
        if (is_attribute_type_array(attribute_type) and
                schema_items and schema_items.get('properties', {})):
            array_schema = schema_items
            array_schema = modify_schema_allow_default_none(schema=array_schema)
            schema['properties'][property_name]['items'] = array_schema

        # Object
        if is_attribute_type_object(attribute_type) and property_data.get('properties', {}):
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


def validate_runner_parameter_attribute_override(action_ref, param_name, attr_name,
                                                 runner_param_attr_value, action_param_attr_value):
    """
    Validate that the provided parameter from the action schema can override the
    runner parameter.
    """
    param_values_are_the_same = action_param_attr_value == runner_param_attr_value
    if (attr_name not in RUNNER_PARAM_OVERRIDABLE_ATTRS and not param_values_are_the_same):
        raise InvalidActionParameterException(
            'The attribute "%s" for the runner parameter "%s" in action "%s" '
            'cannot be overridden.' % (attr_name, param_name, action_ref))

    return True


def get_schema_for_action_parameters(action_db):
    """
    Dynamically construct JSON schema for the provided action from the parameters metadata.

    Note: This schema is used to validate parameters which are passed to the action.
    """
    from st2common.util.action_db import get_runnertype_by_name
    runner_type = get_runnertype_by_name(action_db.runner_type['name'])

    # Note: We need to perform a deep merge because user can only specify a single parameter
    # attribute when overriding it in an action metadata.
    parameters_schema = {}
    deep_update(parameters_schema, runner_type.runner_parameters)
    deep_update(parameters_schema, action_db.parameters)

    # Perform validation, make sure user is not providing parameters which can't
    # be overriden
    runner_parameter_names = runner_type.runner_parameters.keys()

    for name, schema in six.iteritems(action_db.parameters):
        if name not in runner_parameter_names:
            continue

        for attribute, value in six.iteritems(schema):
            runner_param_value = runner_type.runner_parameters[name].get(attribute)
            validate_runner_parameter_attribute_override(action_ref=action_db.ref,
                                                         param_name=name,
                                                         attr_name=attribute,
                                                         runner_param_attr_value=runner_param_value,
                                                         action_param_attr_value=value)

    schema = get_schema_for_resource_parameters(parameters_schema=parameters_schema)

    if parameters_schema:
        schema['title'] = action_db.name
        if action_db.description:
            schema['description'] = action_db.description

    return schema


def get_schema_for_resource_parameters(parameters_schema, allow_additional_properties=False):
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
        schema['additionalProperties'] = allow_additional_properties

    return schema
