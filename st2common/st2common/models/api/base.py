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
import traceback
from oslo_config import cfg

from st2common.constants.pack import DEFAULT_PACK_NAME
from st2common.util import mongoescape as util_mongodb
from st2common.util import schema as util_schema
from st2common.util.debugging import is_enabled as is_debugging_enabled
from st2common.util.jsonify import json_encode
from st2common.util.api import get_exception_for_type_error
from st2common import log as logging

__all__ = [
    'BaseAPI',

    'APIUIDMixin',

    'jsexpose'
]


LOG = logging.getLogger(__name__)


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
        """
        Perform validation and return cleaned object on success.

        Note: This method doesn't mutate this object in place, but it returns a new one.

        :return: Cleaned / validated object.
        """
        schema = getattr(self, 'schema', {})
        attributes = vars(self)

        cleaned = util_schema.validate(instance=attributes, schema=schema,
                                       cls=util_schema.CustomValidator, use_default=True,
                                       allow_default_none=True)

        # Note: We use type() instead of self.__class__ since self.__class__ confuses pylint
        return type(self)(**cleaned)

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


class APIUIDMixin(object):
    """"
    Mixin class for retrieving UID for API objects.
    """

    def get_uid(self):
        # TODO: This is not the most efficient approach - refactor this functionality into util
        # module and re-use it here and in the DB model
        resource_db = self.to_model(self)
        resource_uid = resource_db.get_uid()
        return resource_uid

    def get_pack_uid(self):
        # TODO: This is not the most efficient approach - refactor this functionality into util
        # module and re-use it here and in the DB model
        resource_db = self.to_model(self)
        pack_uid = resource_db.get_pack_uid()
        return pack_uid


def cast_argument_value(value_type, value):
    if value_type == bool:
        def cast_func(value):
            value = str(value)
            return value.lower() in ['1', 'true']
    else:
        cast_func = value_type

    result = cast_func(value)
    return result


def get_controller_args_for_types(func, arg_types, args, kwargs):
    """
    Build a list of arguments and dictionary of keyword arguments which are passed to the
    controller method based on the arg_types specification.

    Note: args argument is mutated in place.
    """
    result_args = []
    result_kwargs = {}

    argspec = inspect.getargspec(func)
    names = argspec.args[1:]  # Note: we skip "self"

    for index, name in enumerate(names):
        # 1. Try kwargs first
        if name in kwargs:
            try:
                value = kwargs[name]
                value_type = arg_types[index]
                value = cast_argument_value(value_type=value_type, value=value)
                result_kwargs[name] = value
            except IndexError:
                LOG.warning("Type definition for '%s' argument of '%s' is missing.",
                            name, func.__name__)

            continue

        # 2. Try positional args
        try:
            value = args.pop(0)
            value_type = arg_types[index]
            value = cast_argument_value(value_type=value_type, value=value)
            result_args.append(value)
        except IndexError:
            LOG.warning("Type definition for '%s' argument of '%s' is missing.",
                        name, func.__name__)

    return result_args, result_kwargs


def jsexpose(arg_types=None, body_cls=None, status_code=None, content_type='application/json',
             method=None):
    """
    :param arg_types: A list of types for the function arguments (e.g. [str, str, int, bool]).
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
            function_name = f.__name__
            args = list(args)
            more = [args.pop(0)]

            def cast_value(value_type, value):
                if value_type == bool:
                    def cast_func(value):
                        return value.lower() in ['1', 'true']
                else:
                    cast_func = value_type

                result = cast_func(value)
                return result

            if body_cls:
                if pecan.request.body:
                    data = pecan.request.json

                    obj = body_cls(**data)
                    try:
                        obj = obj.validate()
                    except (jsonschema.ValidationError, ValueError) as e:
                        raise exc.HTTPBadRequest(detail=e.message,
                                                 comment=traceback.format_exc())
                    except Exception as e:
                        raise exc.HTTPInternalServerError(detail=e.message,
                                                          comment=traceback.format_exc())

                    # Set default pack if one is not provided for resource create
                    if function_name == 'post' and not hasattr(obj, 'pack'):
                        extra = {
                            'resource_api': obj,
                            'default_pack_name': DEFAULT_PACK_NAME
                        }
                        LOG.debug('Pack not provided in the body, setting a default pack name',
                                  extra=extra)
                        setattr(obj, 'pack', DEFAULT_PACK_NAME)
                else:
                    obj = None

                more.append(obj)

            if arg_types:
                # Cast and transform arguments based on the provided arg_types specification
                result_args, result_kwargs = get_controller_args_for_types(func=f,
                                                                           arg_types=arg_types,
                                                                           args=args,
                                                                           kwargs=kwargs)
                more = more + result_args
                kwargs.update(result_kwargs)

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
                e = get_exception_for_type_error(func=f, exc=e)
                raise e

            if status_code:
                pecan.response.status = status_code
            if content_type == 'application/json':
                if is_debugging_enabled():
                    indent = 4
                else:
                    indent = None
                return json_encode(result, indent=indent)
            else:
                return result

        pecan_json_decorate(callfunction)

        return callfunction

    return decorate
