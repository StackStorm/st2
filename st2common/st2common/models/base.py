import abc
import functools
import inspect
import jsonschema
import jsonschema.validators
import pecan
import pecan.jsonify
import six
from webob import exc

from st2common import log as logging

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)


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


Validator = extend_with_default(jsonschema.Draft4Validator)


@six.add_metaclass(abc.ABCMeta)
class BaseAPI(object):
    schema = abc.abstractproperty

    def __init__(self, **kw):
        Validator(getattr(self, 'schema', {})).validate(kw)

        for key, value in kw.items():
            setattr(self, key, value)

    def __repr__(self):
        name = type(self).__name__
        attrs = ', '.join("'%s':%r" % item for item in six.iteritems(vars(self)))
        # The format here is so that eval can be applied.
        return "%s(**{%s})" % (name, attrs)

    def __str__(self):
        name = type(self).__name__
        attrs = ', '.join("%s=%r" % item for item in six.iteritems(vars(self)))

        return "%s[%s]" % (name, attrs)

    def __json__(self):
        return vars(self)

    @classmethod
    def _from_model(cls, model):
        doc = model.to_mongo()
        if '_id' in doc:
            doc['id'] = str(doc.pop('_id'))
        return doc

    @classmethod
    def from_model(cls, model):
        doc = cls._from_model(model)
        return cls(**doc)

    @classmethod
    def to_model(cls, doc):
        model = cls.model()
        setattr(model, 'name', getattr(doc, 'name', None))
        setattr(model, 'description', getattr(doc, 'description', None))
        return model


def jsexpose(*argtypes, **opts):
    pecan_json_decorate = pecan.expose(
        content_type='application/json',
        generic=False)

    def decorate(f):
        @functools.wraps(f)
        def callfunction(*args, **kwargs):
            try:
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
                                LOG.warning("Type definition for '%s' argument of '%s' "
                                            "is missing.", name, f.__name__)
                            except KeyError:
                                pass

                body_cls = opts.get('body')
                if body_cls and pecan.request.body:
                    obj = body_cls(**pecan.request.json)
                    more.append(obj)

                args = tuple(more) + tuple(args)

                status_code = opts.get('status_code')

                noop_codes = [http_client.NOT_IMPLEMENTED,
                              http_client.METHOD_NOT_ALLOWED,
                              http_client.FORBIDDEN]

                if status_code and status_code in noop_codes:
                    pecan.response.status = status_code
                    return pecan.jsonify.encode(None)

                try:
                    result = f(*args, **kwargs)
                    if status_code:
                        pecan.response.status = status_code
                    return pecan.jsonify.encode(result)
                except exc.HTTPException as e:
                    pecan.response.status = e.wsgi_response.status
                    error = {'faultstring': str(e)}
                    return pecan.jsonify.encode(error)
                except Exception as e:
                    pecan.response.status = http_client.INTERNAL_SERVER_ERROR
                    error = {'faultstring': str(e)}
                    return pecan.jsonify.encode(error)

            except Exception as e:
                LOG.error(e)
                pecan.abort(http_client.BAD_REQUEST, str(e))

        pecan_json_decorate(callfunction)

        return callfunction

    return decorate
