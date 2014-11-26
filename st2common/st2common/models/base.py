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

import abc
import functools
import inspect

import jsonschema
import six
from six.moves import http_client
from webob import exc
import pecan
import pecan.jsonify

from st2common.util import mongoescape as util_mongodb
from st2common.util import schema as util_schema
from st2common.util.jsonify import json_encode
from st2common import log as logging


LOG = logging.getLogger(__name__)
VALIDATOR = util_schema.get_validator(assign_property_default=False)


@six.add_metaclass(abc.ABCMeta)
class BaseAPI(object):
    schema = abc.abstractproperty

    def __init__(self, **kw):
        VALIDATOR(getattr(self, 'schema', {})).validate(kw)

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
        doc = util_mongodb.unescape_chars(model.to_mongo())
        if '_id' in doc:
            doc['id'] = str(doc.pop('_id'))
        return doc

    @classmethod
    def from_model(cls, model):
        doc = cls._from_model(model)
        attrs = {attr: value for attr, value in six.iteritems(doc) if value is not None}
        return cls(**attrs)

    @classmethod
    def to_model(cls, doc):
        model = cls.model()
        setattr(model, 'name', getattr(doc, 'name', None))
        setattr(model, 'description', getattr(doc, 'description', None))
        return model


def _handle_error(status, exception):
    LOG.error(exception)
    pecan.response.status = status
    error = {'faultstring': exception.message}
    return json_encode(error)


def jsexpose(*argtypes, **opts):
    content_type = opts.get('content_type', 'application/json')

    pecan_json_decorate = pecan.expose(
        content_type=content_type,
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
                if body_cls:
                    if pecan.request.body:
                        try:
                            obj = body_cls(**pecan.request.json)
                        except jsonschema.exceptions.ValidationError as e:
                            return _handle_error(http_client.BAD_REQUEST, e)
                        more.append(obj)
                    else:
                        more.append(None)

                args = tuple(more) + tuple(args)

                status_code = opts.get('status_code')

                noop_codes = [http_client.NOT_IMPLEMENTED,
                              http_client.METHOD_NOT_ALLOWED,
                              http_client.FORBIDDEN]

                if status_code and status_code in noop_codes:
                    pecan.response.status = status_code
                    return json_encode(None)

                try:
                    result = f(*args, **kwargs)
                    if status_code:
                        pecan.response.status = status_code
                    if content_type == 'application/json':
                        return json_encode(result)
                    else:
                        return result
                except exc.HTTPException as e:
                    return _handle_error(e.wsgi_response.status, e)

            except Exception as e:
                return _handle_error(http_client.INTERNAL_SERVER_ERROR, e)

        pecan_json_decorate(callfunction)

        return callfunction

    return decorate
