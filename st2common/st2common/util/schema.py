import six
import jsonschema
from oslo.config import cfg

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

ACTION_PARAMS_SCHEMA = {
    "title": "ActionPatametersSchema",
    "description": "Schema for validating action parameters",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "description": {"type": "string"},
        "default": {},
        "optional": {"type": "boolean", "default": False},
        "type": {
            "type": "string"
        },
        "position": {
            "type": "number",
            "minimum": 0
        },
        "immutable": {
            "type": "boolean",
            "default": False
        }
    },
    "default": {},
    'additionalProperties': False
}


def get_draft_schema():
    return ACTION_PARAMS_SCHEMA


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
    # Any 'required' runner parameter which is provided in the action is no longer
    # considered 'required' by the runner. The action could choose to keep it
    # 'required' but will have to explicitly call it out.
    runner_required_parameters = [p for p in _get_required_runner_params(runner_type)
                                  if p not in model.parameters]
    required = list(set(runner_required_parameters + _get_required_action_params(model)))
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


def _get_required_action_params(model):
    action_parameters = model.parameters
    required = [param for param, meta in six.iteritems(action_parameters)
                if meta.get('required', None)]
    return required


def _get_required_runner_params(model):
    runner_parameters = model.runner_parameters
    required = [param for param, meta in six.iteritems(runner_parameters)
                if meta.get('required', None)]
    return required
