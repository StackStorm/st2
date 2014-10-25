import os

import six
import jsonschema
from oslo.config import cfg

from st2common.util import jsonify


# https://github.com/json-schema/json-schema/blob/master/draft-04/schema
# The source material is licensed under the AFL or BSD license.
PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)))
SCHEMA_DRAFT4 = jsonify.load_file('%s/draft4.json' % PATH)
SCHEMA_ACTION_PARAMS = jsonify.load_file('%s/action_params.json' % PATH)

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


def get_standard_draft_schema():
    return SCHEMA_DRAFT4


def get_action_params_schema():
    return SCHEMA_ACTION_PARAMS


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
    runner_required_parameters = [p for p in runner_type.required_parameters
                                  if p not in model.parameters]
    required = list(set(runner_required_parameters + model.required_parameters))
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
