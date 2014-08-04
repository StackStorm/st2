import abc
import functools
import inspect
import jsonschema
import jsonschema.validators
import pecan
import pecan.jsonify
import six

from st2common import log as logging

LOG = logging.getLogger(__name__)


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
        return vars(self)


def jsexpose(*argtypes, **opts):
    pecan_json_decorate = pecan.expose(
        content_type='application/json',
        generic=False)

    def decorate(f):
        @functools.wraps(f)
        def callfunction(*args, **kwargs):
            args = list(args)
            types = list(argtypes)
            more = [args.pop(0)]

            if len(types):
                argspec = inspect.getargspec(f)
                names = argspec.args[1:]

                for name in names:
                    try:
                        a = args.pop(0)
                        more.append(types.pop(0)(a))
                    except IndexError:
                        try:
                            kwargs[name] = types.pop(0)(kwargs[name])
                        except IndexError:
                            LOG.warning("Type definition for '%s' argument of '%s' is missing.",
                                        name, f.__name__)
                        except KeyError:
                            pass

            body_cls = opts.get('body')
            if body_cls:
                more.append(body_cls(**pecan.request.json))

            args = tuple(more) + tuple(args)

            result = f(*args, **kwargs)

            status_code = opts.get('status_code')
            if status_code:
                pecan.response.status = status_code

            return pecan.jsonify.encode(result)

        pecan_json_decorate(callfunction)

        return callfunction

    return decorate