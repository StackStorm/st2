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

import re
import abc
import copy
import functools
import inspect

import jsonschema
import six
from six.moves import http_client
from webob import exc
import pecan
import pecan.jsonify
import traceback
from oslo_config import cfg

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
        for key, value in kw.items():
            setattr(self, key, value)

    def __repr__(self):
        name = type(self).__name__
        attrs = ', '.join("'%s': %r" % item for item in six.iteritems(vars(self)))
        # The format here is so that eval can be applied.
        return "%s(**{%s})" % (name, attrs)

    def __str__(self):
        name = type(self).__name__
        attrs = ', '.join("%s=%r" % item for item in six.iteritems(vars(self)))

        return "%s[%s]" % (name, attrs)

    def __json__(self):
        return vars(self)

    def validate(self):
        VALIDATOR(getattr(self, 'schema', {})).validate(vars(self))

    @classmethod
    def _from_model(cls, model, mask_secrets=False):
        doc = util_mongodb.unescape_chars(model.to_mongo())

        if '_id' in doc:
            doc['id'] = str(doc.pop('_id'))

        if mask_secrets and cfg.CONF.log.mask_secrets:
            doc = model.mask_secrets(value=doc)

        return doc

    @classmethod
    def from_model(cls, model, mask_secrets=False):
        """
        Create API model class instance for the provided DB model instance.

        :param model: DB model class instance.
        :type model: :class:`StormFoundationDB`

        :param mask_secrets: True to mask secrets in the resulting instance.
        :type mask_secrets: ``boolean``
        """
        doc = cls._from_model(model=model, mask_secrets=mask_secrets)
        attrs = {attr: value for attr, value in six.iteritems(doc) if value is not None}

        return cls(**attrs)

    @classmethod
    def to_model(cls, doc):
        """
        Create a model class instance for the provided MongoDB document.

        :param doc: MongoDB document.
        """
        raise NotImplementedError()


def jsexpose(arg_types=None, body_cls=None, status_code=None, content_type='application/json'):
    """
    :param arg_types: A list of types for the function arguments.
    :type arg_types: ``list``

    :param body_cls: Request body class. If provided, this class will be used to create an instance
                     out of the request body.
    :type body_cls: :class:`object`

    :param status_code: Response status code.
    :type status_code: ``int``

    :param content_type: Response content type.
    :type content_type: ``str``
    """
    pecan_json_decorate = pecan.expose(
        content_type=content_type,
        generic=False)

    def decorate(f):
        @functools.wraps(f)
        def callfunction(*args, **kwargs):
            args = list(args)
            types = copy.copy(arg_types)
            more = [args.pop(0)]

            if types:
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

            if body_cls:
                if pecan.request.body:
                    data = pecan.request.json
                else:
                    data = {}

                obj = body_cls(**data)
                try:
                    obj.validate()
                except jsonschema.ValidationError as e:
                    raise exc.HTTPBadRequest(detail=e.message,
                                             comment=traceback.format_exc())
                except Exception as e:
                    raise exc.HTTPInternalServerError(detail=e.message,
                                                      comment=traceback.format_exc())
                more.append(obj)

            args = tuple(more) + tuple(args)

            noop_codes = [http_client.NOT_IMPLEMENTED,
                          http_client.METHOD_NOT_ALLOWED,
                          http_client.FORBIDDEN]

            if status_code and status_code in noop_codes:
                pecan.response.status = status_code
                return json_encode(None)

            try:
                result = f(*args, **kwargs)
            except TypeError as e:
                message = str(e)
                # Invalid number of arguments passed to the function meaning invalid path was
                # requested
                # Note: The check is hacky, but it works for now.
                if re.search('takes exactly \d+ arguments \(\d+ given\)', message):
                    raise exc.HTTPNotFound()
                else:
                    raise e

            if status_code:
                pecan.response.status = status_code
            if content_type == 'application/json':
                return json_encode(result, indent=None)
            else:
                return result

        pecan_json_decorate(callfunction)

        return callfunction

    return decorate
