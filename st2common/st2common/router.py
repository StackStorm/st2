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

from __future__ import absolute_import
import copy
import functools
import re
import six
import sys
import traceback

from flex.core import validate
import jsonschema
from oslo_config import cfg
import routes
from six.moves.urllib import parse as urlparse  # pylint: disable=import-error
import webob
from webob import cookies, exc, Request
from webob.compat import url_unquote

from st2common.exceptions import rbac as rbac_exc
from st2common.exceptions import auth as auth_exc
from st2common import log as logging
from st2common.persistence.auth import User
from st2common.rbac.backends import get_backend_instance
from st2common.util import date as date_utils
from st2common.util.jsonify import json_encode
from st2common.util.jsonify import get_json_type_for_python_value
from st2common.util.http import parse_content_type_header

__all__ = [
    'Router',

    'Response',

    'NotFoundException',

    'abort',
    'abort_unauthorized',
    'exc'
]

LOG = logging.getLogger(__name__)


def op_resolver(op_id):
    """
    Return controller class instance and controller method callbacle for the provided operation id.

    :rtype: ``tuple``
    """
    module_name, func_name = op_id.split(':', 1)
    controller_name = func_name.split('.')[0]

    __import__(module_name)
    module = sys.modules[module_name]

    controller_instance = getattr(module, controller_name)
    method_callable = functools.reduce(getattr, func_name.split('.'), module)

    return controller_instance, method_callable


def abort(status_code=exc.HTTPInternalServerError.code, message='Unhandled exception'):
    raise exc.status_map[status_code](message)


def abort_unauthorized(msg=None):
    raise exc.HTTPUnauthorized('Unauthorized - %s' % msg if msg else 'Unauthorized')


def extend_with_default(validator_class):
    validate_properties = validator_class.VALIDATORS["properties"]

    def set_defaults(validator, properties, instance, schema):
        for property, subschema in six.iteritems(properties):
            if "default" in subschema:
                instance.setdefault(property, subschema["default"])

        for error in validate_properties(
            validator, properties, instance, schema,
        ):
            yield error

    return jsonschema.validators.extend(
        validator_class, {"properties": set_defaults},
    )


def extend_with_additional_check(validator_class):
    def set_additional_check(validator, properties, instance, schema):
        ref = schema.get("x-additional-check")
        _, func = op_resolver(ref)
        for error in func(validator, properties, instance, schema):
            yield error

    return jsonschema.validators.extend(
        validator_class, {"x-additional-check": set_additional_check},
    )


def extend_with_nullable(validator_class):
    validate_type = validator_class.VALIDATORS["type"]

    def set_type_draft4(validator, types, instance, schema):
        is_nullable = schema.get("x-nullable", False)

        if is_nullable and instance is None:
            return

        for error in validate_type(validator, types, instance, schema):
            yield error

    return jsonschema.validators.extend(
        validator_class, {"type": set_type_draft4},
    )


CustomValidator = jsonschema.Draft4Validator
CustomValidator = extend_with_nullable(CustomValidator)
CustomValidator = extend_with_additional_check(CustomValidator)
CustomValidator = extend_with_default(CustomValidator)


class NotFoundException(Exception):
    pass


class Response(webob.Response):
    def __init__(self, body=None, status=None, headerlist=None, app_iter=None, content_type=None,
                 *args, **kwargs):
        # Do some sanity checking, and turn json_body into an actual body
        if app_iter is None and body is None and ('json_body' in kwargs or 'json' in kwargs):
            if 'json_body' in kwargs:
                json_body = kwargs.pop('json_body')
            else:
                json_body = kwargs.pop('json')
            body = json_encode(json_body).encode('UTF-8')

            if content_type is None:
                content_type = 'application/json'

        super(Response, self).__init__(body, status, headerlist, app_iter, content_type,
                                       *args, **kwargs)

    def _json_body__get(self):
        return super(Response, self)._json_body__get()

    def _json_body__set(self, value):
        self.body = json_encode(value).encode('UTF-8')

    def _json_body__del(self):
        return super(Response, self)._json_body__del()

    json = json_body = property(_json_body__get, _json_body__set, _json_body__del)


class Router(object):
    def __init__(self, arguments=None, debug=False, auth=True, is_gunicorn=True):
        self.debug = debug
        self.auth = auth
        self.is_gunicorn = is_gunicorn

        self.arguments = arguments or {}

        self.spec = {}
        self.spec_resolver = None
        self.routes = routes.Mapper()

    def add_spec(self, spec, transforms):
        info = spec.get('info', {})
        LOG.debug('Adding API: %s %s', info.get('title', 'untitled'), info.get('version', '0.0.0'))

        self.spec = spec
        self.spec_resolver = jsonschema.RefResolver('', self.spec)

        validate(copy.deepcopy(self.spec))

        for filter in transforms:
            for (path, methods) in six.iteritems(spec['paths']):
                if not re.search(filter, path):
                    continue

                for (method, endpoint) in six.iteritems(methods):
                    conditions = {
                        'method': [method.upper()]
                    }

                    connect_kw = {}
                    if 'x-requirements' in endpoint:
                        connect_kw['requirements'] = endpoint['x-requirements']

                    m = self.routes.submapper(_api_path=path, _api_method=method,
                                              conditions=conditions)
                    for transform in transforms[filter]:
                        m.connect(None, re.sub(filter, transform, path), **connect_kw)

                    module_name = endpoint['operationId'].split(':', 1)[0]
                    __import__(module_name)

        for route in sorted(self.routes.matchlist, key=lambda r: r.routepath):
            LOG.debug('Route registered: %+6s %s', route.conditions['method'][0], route.routepath)

    def match(self, req):
        path = url_unquote(req.path)
        LOG.debug("Match path: %s", path)

        if len(path) > 1 and path.endswith('/'):
            path = path[:-1]

        match = self.routes.match(path, req.environ)

        if match is None:
            raise NotFoundException('No route matches "%s" path' % req.path)

        # To account for situation when match may return multiple values
        try:
            path_vars = match[0]
        except KeyError:
            path_vars = match

        path_vars = dict(path_vars)

        path = path_vars.pop('_api_path')
        method = path_vars.pop('_api_method')
        endpoint = self.spec['paths'][path][method]

        return endpoint, path_vars

    def __call__(self, req):
        """
        The method is invoked on every request and shows the lifecycle of the request received from
        the middleware.

        Although some middleware may use parts of the API spec, it is safe to assume that if you're
        looking for the particular spec property handler, it's most likely a part of this method.

        At the time of writing, the only property being utilized by middleware was `x-log-result`.
        """
        LOG.debug("Received call with WebOb: %s", req)
        endpoint, path_vars = self.match(req)
        LOG.debug("Parsed endpoint: %s", endpoint)
        LOG.debug("Parsed path_vars: %s", path_vars)

        context = copy.copy(getattr(self, 'mock_context', {}))
        cookie_token = None

        # Handle security
        if 'security' in endpoint:
            security = endpoint.get('security')
        else:
            security = self.spec.get('security', [])

        if self.auth and security:
            try:
                security_definitions = self.spec.get('securityDefinitions', {})
                for statement in security:
                    declaration, options = statement.copy().popitem()
                    definition = security_definitions[declaration]

                    if definition['type'] == 'apiKey':
                        if definition['in'] == 'header':
                            token = req.headers.get(definition['name'])
                        elif definition['in'] == 'query':
                            token = req.GET.get(definition['name'])
                        elif definition['in'] == 'cookie':
                            token = req.cookies.get(definition['name'])
                        else:
                            token = None

                        if token:
                            _, auth_func = op_resolver(definition['x-operationId'])
                            auth_resp = auth_func(token)

                            # Include information on how user authenticated inside the context
                            if 'auth-token' in definition['name'].lower():
                                auth_method = 'authentication token'
                            elif 'api-key' in definition['name'].lower():
                                auth_method = 'API key'

                            context['user'] = User.get_by_name(auth_resp.user)
                            context['auth_info'] = {
                                'method': auth_method,
                                'location': definition['in']
                            }

                            # Also include token expiration time when authenticated via auth token
                            if 'auth-token' in definition['name'].lower():
                                context['auth_info']['token_expire'] = auth_resp.expiry

                            if 'x-set-cookie' in definition:
                                max_age = auth_resp.expiry - date_utils.get_datetime_utc_now()
                                cookie_token = cookies.make_cookie(definition['x-set-cookie'],
                                                                   token,
                                                                   max_age=max_age,
                                                                   httponly=True)

                            break

                if 'user' not in context:
                    raise auth_exc.NoAuthSourceProvidedError('One of Token or API key required.')
            except (auth_exc.NoAuthSourceProvidedError,
                    auth_exc.MultipleAuthSourcesError) as e:
                LOG.error(six.text_type(e))
                return abort_unauthorized(six.text_type(e))
            except auth_exc.TokenNotProvidedError as e:
                LOG.exception('Token is not provided.')
                return abort_unauthorized(six.text_type(e))
            except auth_exc.TokenNotFoundError as e:
                LOG.exception('Token is not found.')
                return abort_unauthorized(six.text_type(e))
            except auth_exc.TokenExpiredError as e:
                LOG.exception('Token has expired.')
                return abort_unauthorized(six.text_type(e))
            except auth_exc.ApiKeyNotProvidedError as e:
                LOG.exception('API key is not provided.')
                return abort_unauthorized(six.text_type(e))
            except auth_exc.ApiKeyNotFoundError as e:
                LOG.exception('API key is not found.')
                return abort_unauthorized(six.text_type(e))
            except auth_exc.ApiKeyDisabledError as e:
                LOG.exception('API key is disabled.')
                return abort_unauthorized(six.text_type(e))

            if cfg.CONF.rbac.enable:
                user_db = context['user']

                permission_type = endpoint.get('x-permissions', None)
                if permission_type:
                    rbac_backend = get_backend_instance(cfg.CONF.rbac.backend)

                    resolver = rbac_backend.get_resolver_for_permission_type(permission_type)
                    has_permission = resolver.user_has_permission(user_db, permission_type)

                    if not has_permission:
                        raise rbac_exc.ResourceTypeAccessDeniedError(user_db,
                                                                     permission_type)

        # Collect parameters
        kw = {}
        for param in endpoint.get('parameters', []) + endpoint.get('x-parameters', []):
            name = param['name']
            argument_name = param.get('x-as', None) or name
            source = param['in']
            default = param.get('default', None)

            # Collecting params from different sources
            if source == 'query':
                kw[argument_name] = req.GET.get(name, default)
            elif source == 'path':
                kw[argument_name] = path_vars[name]
            elif source == 'header':
                kw[argument_name] = req.headers.get(name, default)
            elif source == 'formData':
                kw[argument_name] = req.POST.get(name, default)
            elif source == 'environ':
                kw[argument_name] = req.environ.get(name.upper(), default)
            elif source == 'context':
                kw[argument_name] = context.get(name, default)
            elif source == 'request':
                kw[argument_name] = getattr(req, name)
            elif source == 'body':
                content_type = req.headers.get('Content-Type', 'application/json')
                content_type = parse_content_type_header(content_type=content_type)[0]
                schema = param['schema']

                # NOTE: HACK: Workaround for eventlet wsgi server which sets Content-Type to
                # text/plain if Content-Type is not provided in the request.
                # All ouf our API endpoints except /v1/workflows/inspection and
                # /exp/validation/mistral expect application/json so we explicitly set it to that
                # if not provided (set to text/plain by the base http server) and if it's not
                # /v1/workflows/inspection and /exp/validation/mistral API endpoints.
                if not self.is_gunicorn and content_type == 'text/plain':
                    operation_id = endpoint['operationId']

                    if ('workflow_inspection_controller' not in operation_id and
                            'mistral_validation_controller' not in operation_id):
                        content_type = 'application/json'

                # Note: We also want to perform validation if no body is explicitly provided - in a
                # lot of POST, PUT scenarios, body is mandatory
                if not req.body and content_type == 'application/json':
                    req.body = b'{}'

                try:
                    if content_type == 'application/json':
                        data = req.json
                    elif content_type == 'text/plain':
                        data = req.body
                    elif content_type in ['application/x-www-form-urlencoded',
                                          'multipart/form-data']:
                        data = urlparse.parse_qs(req.body)
                    else:
                        raise ValueError('Unsupported Content-Type: "%s"' % (content_type))
                except Exception as e:
                    detail = 'Failed to parse request body: %s' % six.text_type(e)
                    raise exc.HTTPBadRequest(detail=detail)

                # Special case for Python 3
                if six.PY3 and content_type == 'text/plain' and isinstance(data, six.binary_type):
                    # Convert bytes to text type (string / unicode)
                    data = data.decode('utf-8')

                try:
                    CustomValidator(schema, resolver=self.spec_resolver).validate(data)
                except (jsonschema.ValidationError, ValueError) as e:
                    raise exc.HTTPBadRequest(detail=getattr(e, 'message', six.text_type(e)),
                                             comment=traceback.format_exc())

                if content_type == 'text/plain':
                    kw[argument_name] = data
                else:
                    class Body(object):
                        def __init__(self, **entries):
                            self.__dict__.update(entries)

                    ref = schema.get('$ref', None)
                    if ref:
                        with self.spec_resolver.resolving(ref) as resolved:
                            schema = resolved

                    if 'x-api-model' in schema:
                        input_type = schema.get('type', [])
                        _, Model = op_resolver(schema['x-api-model'])

                        if input_type and not isinstance(input_type, (list, tuple)):
                            input_type = [input_type]

                        # root attribute is not an object, we need to use wrapper attribute to
                        # make it work with **kwarg expansion
                        if input_type and 'array' in input_type:
                            data = {'data': data}

                        instance = self._get_model_instance(model_cls=Model, data=data)

                        # Call validate on the API model - note we should eventually move all
                        # those model schema definitions into openapi.yaml
                        try:
                            instance = instance.validate()
                        except (jsonschema.ValidationError, ValueError) as e:
                            raise exc.HTTPBadRequest(detail=getattr(e, 'message', six.text_type(e)),
                                                     comment=traceback.format_exc())
                    else:
                        LOG.debug('Missing x-api-model definition for %s, using generic Body '
                                  'model.' % (endpoint['operationId']))
                        model = Body
                        instance = self._get_model_instance(model_cls=model, data=data)

                    kw[argument_name] = instance

            # Making sure all required params are present
            required = param.get('required', False)
            if required and kw[argument_name] is None:
                detail = 'Required parameter "%s" is missing' % name
                raise exc.HTTPBadRequest(detail=detail)

            # Validating and casting param types
            param_type = param.get('type', None)
            if kw[argument_name] is not None:
                if param_type == 'boolean':
                    positive = ('true', '1', 'yes', 'y')
                    negative = ('false', '0', 'no', 'n')

                    if str(kw[argument_name]).lower() not in positive + negative:
                        detail = 'Parameter "%s" is not of type boolean' % argument_name
                        raise exc.HTTPBadRequest(detail=detail)

                    kw[argument_name] = str(kw[argument_name]).lower() in positive
                elif param_type == 'integer':
                    regex = r'^-?[0-9]+$'

                    if not re.search(regex, str(kw[argument_name])):
                        detail = 'Parameter "%s" is not of type integer' % argument_name
                        raise exc.HTTPBadRequest(detail=detail)

                    kw[argument_name] = int(kw[argument_name])
                elif param_type == 'number':
                    regex = r'^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$'

                    if not re.search(regex, str(kw[argument_name])):
                        detail = 'Parameter "%s" is not of type float' % argument_name
                        raise exc.HTTPBadRequest(detail=detail)

                    kw[argument_name] = float(kw[argument_name])
                elif param_type == 'array' and param.get('items', {}).get('type', None) == 'string':
                    if kw[argument_name] is None:
                        kw[argument_name] = []
                    elif isinstance(kw[argument_name], (list, tuple)):
                        # argument is already an array
                        pass
                    else:
                        kw[argument_name] = kw[argument_name].split(',')

        # Call the controller
        try:
            controller_instance, func = op_resolver(endpoint['operationId'])
        except Exception as e:
            LOG.exception('Failed to load controller for operation "%s": %s' %
                          (endpoint['operationId'], six.text_type(e)))
            raise e

        try:
            resp = func(**kw)
        except Exception as e:
            LOG.exception('Failed to call controller function "%s" for operation "%s": %s' %
                          (func.__name__, endpoint['operationId'], six.text_type(e)))
            raise e

        # Handle response
        if resp is None:
            resp = Response()

        if not hasattr(resp, '__call__'):
            resp = Response(json=resp)

        operation_id = endpoint['operationId']

        # Process the response removing attributes based on the exclude_attribute and
        # include_attributes query param filter values (if specified)
        include_attributes = kw.get('include_attributes', None)
        exclude_attributes = kw.get('exclude_attributes', None)
        has_include_or_exclude_attributes = bool(include_attributes) or bool(exclude_attributes)

        # NOTE: We do NOT want to process stream controller response
        is_streamming_controller = endpoint.get('x-is-streaming-endpoint',
                                                bool('st2stream' in operation_id))

        if not is_streamming_controller and resp.body and has_include_or_exclude_attributes:
            # NOTE: We need to check for response.body attribute since resp.json throws if JSON
            # response is not available
            mandatory_include_fields = getattr(controller_instance,
                                               'mandatory_include_fields_response', [])
            data = self._process_response(data=resp.json,
                                          mandatory_include_fields=mandatory_include_fields,
                                          include_attributes=include_attributes,
                                          exclude_attributes=exclude_attributes)
            resp.json = data

        responses = endpoint.get('responses', {})
        response_spec = responses.get(str(resp.status_code), None)
        default_response_spec = responses.get('default', None)

        if not response_spec and default_response_spec:
            LOG.debug('No custom response spec found for endpoint "%s", using a default one' %
                      (endpoint['operationId']))
            response_spec_name = 'default'
        else:
            response_spec_name = str(resp.status_code)

        response_spec = response_spec or default_response_spec

        if response_spec and 'schema' in response_spec and not has_include_or_exclude_attributes:
            # NOTE: We don't perform response validation when include or exclude attributes are
            # provided because this means partial response which likely won't pass the validation
            LOG.debug('Using response spec "%s" for endpoint %s and status code %s' %
                     (response_spec_name, endpoint['operationId'], resp.status_code))

            try:
                validator = CustomValidator(response_spec['schema'], resolver=self.spec_resolver)

                response_type = response_spec['schema'].get('type', 'json')
                if response_type == 'string':
                    validator.validate(resp.text)
                else:
                    validator.validate(resp.json)
            except (jsonschema.ValidationError, ValueError):
                LOG.exception('Response validation failed.')
                resp.headers.add('Warning', '199 OpenAPI "Response validation failed"')
        else:
            LOG.debug('No response spec found for endpoint "%s"' % (endpoint['operationId']))

        if cookie_token:
            resp.headerlist.append(('Set-Cookie', cookie_token))

        return resp

    def as_wsgi(self, environ, start_response):
        """
        Converts WSGI request to webob.Request and initiates the response returned by controller.
        """
        req = Request(environ)
        resp = self(req)
        return resp(environ, start_response)

    def _get_model_instance(self, model_cls, data):
        try:
            instance = model_cls(**data)
        except TypeError as e:
            # Throw a more user-friendly exception when input data is not an object
            if 'type object argument after ** must be a mapping, not' in six.text_type(e):
                type_string = get_json_type_for_python_value(data)
                msg = ('Input body needs to be an object, got: %s' % (type_string))
                raise ValueError(msg)

            raise e

        return instance

    def _process_response(self, data, mandatory_include_fields=None, include_attributes=None,
                          exclude_attributes=None):
        """
        Process controller response data such as removing attributes based on the values of
        exclude_attributes and include_attributes query param filters and similar.

        :param data: Response data.
        :type: data: ``list`` or ``dict``
        """
        mandatory_include_fields = mandatory_include_fields or []
        include_attributes = include_attributes or []
        exclude_attributes = exclude_attributes or []

        # NOTE: include_attributes and exclude_attributes are mutually exclusive
        if include_attributes and exclude_attributes:
            msg = ('exclude_attributes and include_attributes arguments are mutually exclusive. '
                   'You need to provide either one or another, but not both.')
            raise ValueError(msg)

        #  Common case - filters are not provided
        if not include_attributes and not exclude_attributes:
            return data

        # Skip processing of error responses
        if isinstance(data, dict) and data.get('faultstring', None):
            return data

        # We only care about the first part of the field name since deep filtering happens inside
        # MongoDB. Deep filtering here would also be quite expensive and waste of CPU cycles.
        cleaned_include_attributes = [attribute.split('.')[0] for attribute in include_attributes]

        # Add in mandatory fields which always need to be present in the response (primary keys)
        cleaned_include_attributes += mandatory_include_fields
        cleaned_exclude_attributes = [attribute.split('.')[0] for attribute in exclude_attributes]

        # NOTE: Since those parameters are mutually exclusive we could perform more efficient
        # filtering when just exclude_attributes is provided. Instead of creating a new dict, we
        # could just manipulate (delete) from the existing one.
        def process_item(item):
            result = {}
            for name, value in six.iteritems(item):
                if include_attributes and name not in cleaned_include_attributes:
                    continue

                if exclude_attributes and name in cleaned_exclude_attributes:
                    continue

                result[name] = value

            return result

        result = None
        if isinstance(data, (list, tuple)):
            # get_all response
            result = []
            for item in data:
                item = process_item(item)
                result.append(item)
        elif isinstance(data, dict):
            # get_one response
            result = process_item(data)
        else:
            raise ValueError('Unsupported type: %s' % (type(data)))

        return result
