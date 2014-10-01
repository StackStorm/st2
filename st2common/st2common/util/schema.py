import six
import jsonschema
from oslo.config import cfg


# https://github.com/json-schema/json-schema/blob/master/draft-04/schema
# The source material is licensed under the AFL or BSD license.
SCHEMA_DRAFT4 = {
    "id": "http://json-schema.org/draft-04/schema#",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "description": "Core schema meta-schema",
    "definitions": {
        "schemaArray": {
            "type": "array",
            "minItems": 1,
            "items": {"$ref": "#"}
        },
        "positiveInteger": {
            "type": "integer",
            "minimum": 0
        },
        "positiveIntegerDefault0": {
            "allOf": [{"$ref": "#/definitions/positiveInteger"}, {"default": 0}]
        },
        "simpleTypes": {
            "enum": ["array", "boolean", "integer", "null", "number", "object", "string"]
        },
        "stringArray": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "uniqueItems": True
        }
    },
    "type": "object",
    "properties": {
        "id": {
            "type": "string",
            "format": "uri"
        },
        "$schema": {
            "type": "string",
            "format": "uri"
        },
        "title": {
            "type": "string"
        },
        "description": {
            "type": "string"
        },
        "default": {},
        "multipleOf": {
            "type": "number",
            "minimum": 0,
            "exclusiveMinimum": True
        },
        "maximum": {
            "type": "number"
        },
        "exclusiveMaximum": {
            "type": "boolean",
            "default": False
        },
        "minimum": {
            "type": "number"
        },
        "exclusiveMinimum": {
            "type": "boolean",
            "default": False
        },
        "maxLength": {"$ref": "#/definitions/positiveInteger"},
        "minLength": {"$ref": "#/definitions/positiveIntegerDefault0"},
        "pattern": {
            "type": "string",
            "format": "regex"
        },
        "additionalItems": {
            "anyOf": [
                {"type": "boolean"},
                {"$ref": "#"}
            ],
            "default": {}
        },
        "items": {
            "anyOf": [
                {"$ref": "#"},
                {"$ref": "#/definitions/schemaArray"}
            ],
            "default": {}
        },
        "maxItems": {"$ref": "#/definitions/positiveInteger"},
        "minItems": {"$ref": "#/definitions/positiveIntegerDefault0"},
        "uniqueItems": {
            "type": "boolean",
            "default": False
        },
        "maxProperties": {"$ref": "#/definitions/positiveInteger"},
        "minProperties": {"$ref": "#/definitions/positiveIntegerDefault0"},
        "required": {"$ref": "#/definitions/stringArray"},
        "additionalProperties": {
            "anyOf": [
                {"type": "boolean"},
                {"$ref": "#"}
            ],
            "default": {}
        },
        "definitions": {
            "type": "object",
            "additionalProperties": {"$ref": "#"},
            "default": {}
        },
        "properties": {
            "type": "object",
            "additionalProperties": {"$ref": "#"},
            "default": {}
        },
        "patternProperties": {
            "type": "object",
            "additionalProperties": {"$ref": "#"},
            "default": {}
        },
        "dependencies": {
            "type": "object",
            "additionalProperties": {
                "anyOf": [
                    {"$ref": "#"},
                    {"$ref": "#/definitions/stringArray"}
                ]
            }
        },
        "enum": {
            "type": "array",
            "minItems": 1,
            "uniqueItems": True
        },
        "type": {
            "anyOf": [
                {"$ref": "#/definitions/simpleTypes"},
                {
                    "type": "array",
                    "items": {"$ref": "#/definitions/simpleTypes"},
                    "minItems": 1,
                    "uniqueItems": True
                }
            ]
        },
        "position": {
            "type": "number",
            "minimum": 0
        },
        "immutable": {
            "type": "boolean",
            "default": False
        },
        "allOf": {"$ref": "#/definitions/schemaArray"},
        "anyOf": {"$ref": "#/definitions/schemaArray"},
        "oneOf": {"$ref": "#/definitions/schemaArray"},
        "not": {"$ref": "#"}
    },
    "dependencies": {
        "exclusiveMaximum": ["maximum"],
        "exclusiveMinimum": ["minimum"]
    },
    "default": {},
    'additionalProperties': False
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


def get_draft_schema():
    return SCHEMA_DRAFT4


def extend_with_default(validator_class):
    validate_properties = validator_class.VALIDATORS["properties"]

    def set_defaults(validator, properties, instance, schema):
        for error in validate_properties(
            validator, properties, instance, schema,
        ):
            yield error

        for property, subschema in six.iteritems(properties):
            if "default" in subschema:
                instance.setdefault(property, subschema["default"])

    return jsonschema.validators.extend(
        validator_class, {"properties": set_defaults},
    )


def get_validator(assign_property_default=False):
    validator = jsonschema.Draft4Validator
    return extend_with_default(validator) if assign_property_default else validator


def get_parameter_schema(model):
    # Dynamically construct JSON schema from the parameters metadata.
    schema = {"$schema": cfg.CONF.schema.draft}
    from st2common.util.action_db import get_runnertype_by_name
    runner_type = get_runnertype_by_name(model.runner_type['name'])
    required = list(set(runner_type.required_parameters + model.required_parameters))
    normalize = lambda x: {k: v if v else SCHEMA_ANY_TYPE for k, v in six.iteritems(x)}
    properties = normalize(runner_type.runner_parameters)
    properties.update(normalize(model.parameters))
    if properties:
        schema['title'] = model.name
        if model.description:
            schema['description'] = model.description
        schema['type'] = 'object'
        schema['properties'] = properties
        if required:
            schema['required'] = required
        schema['additionalProperties'] = False
    return schema
