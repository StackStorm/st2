import abc
import json
import jsonschema
import jsonschema.validators
import six


def extend_with_default(validator_class):
    validate_properties = validator_class.VALIDATORS["properties"]

    def set_defaults(validator, properties, instance, schema):
        for error in validate_properties(
            validator, properties, instance, schema,
        ):
            yield error

        for property, subschema in properties.iteritems():
            if "default" in subschema:
                instance.setdefault(property, subschema["default"])

    return jsonschema.validators.extend(
        validator_class, {"properties" : set_defaults},
    )


Validator = extend_with_default(jsonschema.Draft4Validator)


@six.add_metaclass(abc.ABCMeta)
class BaseAPI(object):
    schema = abc.abstractproperty

    def __init__(self, **kw):
        Validator(getattr(self, 'schema', {})).validate(kw)

        for key, value in kw.items():
            setattr(self, key, value)

    def __str__(self):
        name = type(self).__name__
        attrs = ', '.join("%s=%r" % item for item in vars(self).iteritems())

        return "%s [%s]" % (name, attrs)

    def __json__(self):
        return json.dumps(self, default=lambda o: vars(o))
