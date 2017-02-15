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

import copy
import functools
import six
import sys
import time
import traceback
import uuid

import jsonschema
from mongoengine import ValidationError
from oslo_config import cfg
import routes
from six.moves.urllib import parse as urlparse  # pylint: disable=import-error
from swagger_spec_validator.validator20 import validate_spec
import webob
from webob import exc, Request
from webob.headers import ResponseHeaders

from st2common.constants.api import REQUEST_ID_HEADER
from st2common.constants.auth import HEADER_ATTRIBUTE_NAME
from st2common.constants.auth import HEADER_API_KEY_ATTRIBUTE_NAME
from st2common.exceptions import rbac as rbac_exc
from st2common.exceptions import auth as auth_exc
from st2common.exceptions import db as db_exceptions
from st2common.exceptions import rbac as rbac_exceptions
from st2common.exceptions.apivalidation import ValueValidationException
from st2common import log as logging
from st2common.persistence.auth import User
from st2common.rbac import resolvers
from st2common.util.debugging import is_enabled as is_debugging_enabled
from st2common.util.jsonify import json_encode
from st2common.util.http import parse_content_type_header


LOG = logging.getLogger(__name__)

try:
    clock = time.perf_counter
except AttributeError:
    clock = time.time


def op_resolver(op_id):
    module_name, func_name = op_id.split(':', 1)
    __import__(module_name)
    module = sys.modules[module_name]
    return functools.reduce(getattr, func_name.split('.'), module)


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
        func = op_resolver(ref)
        for error in func(validator, properties, instance, schema):
            yield error

    return jsonschema.validators.extend(
        validator_class, {"x-additional-check": set_additional_check},
    )

CustomValidator = extend_with_default(extend_with_additional_check(jsonschema.Draft4Validator))


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

    def _json_body__set(self, value):
        self.body = json_encode(value).encode('UTF-8')


class ErrorHandlingMiddleware(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        try:
            try:
                return self.app(environ, start_response)
            except NotFoundException:
                raise exc.HTTPNotFound()
        except Exception as e:
            status = getattr(e, 'code', exc.HTTPInternalServerError.code)

            if hasattr(e, 'detail') and not getattr(e, 'comment'):
                setattr(e, 'comment', getattr(e, 'detail'))

            if hasattr(e, 'body') and isinstance(getattr(e, 'body', None), dict):
                body = getattr(e, 'body', None)
            else:
                body = {}

            if isinstance(e, exc.HTTPException):
                status_code = status
                message = str(e)
            elif isinstance(e, db_exceptions.StackStormDBObjectNotFoundError):
                status_code = exc.HTTPNotFound.code
                message = str(e)
            elif isinstance(e, db_exceptions.StackStormDBObjectConflictError):
                status_code = exc.HTTPConflict.code
                message = str(e)
                body['conflict-id'] = getattr(e, 'conflict_id', None)
            elif isinstance(e, rbac_exceptions.AccessDeniedError):
                status_code = exc.HTTPForbidden.code
                message = str(e)
            elif isinstance(e, (ValueValidationException, ValueError, ValidationError)):
                status_code = exc.HTTPBadRequest.code
                message = getattr(e, 'message', str(e))
            else:
                status_code = exc.HTTPInternalServerError.code
                message = 'Internal Server Error'

            # Log the error
            is_internal_server_error = status_code == exc.HTTPInternalServerError.code
            error_msg = getattr(e, 'comment', str(e))
            extra = {
                'exception_class': e.__class__.__name__,
                'exception_message': str(e),
                'exception_data': e.__dict__
            }

            if is_internal_server_error:
                LOG.exception('API call failed: %s', error_msg, extra=extra)
                LOG.exception(traceback.format_exc())
            else:
                LOG.debug('API call failed: %s', error_msg, extra=extra)

                if is_debugging_enabled():
                    LOG.debug(traceback.format_exc())

            body['faultstring'] = message

            response_body = json_encode(body)
            headers = {
                'Content-Type': 'application/json',
                'Content-Length': str(len(response_body))
            }

            resp = Response(response_body, status=status_code, headers=headers)

            return resp(environ, start_response)


class CorsMiddleware(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        request = Request(environ)

        def custom_start_response(status, headers, exc_info=None):
            headers = ResponseHeaders(headers)

            origin = request.headers.get('Origin')
            origins = set(cfg.CONF.api.allow_origin)

            # Build a list of the default allowed origins
            public_api_url = cfg.CONF.auth.api_url

            # Default gulp development server WebUI URL
            origins.add('http://127.0.0.1:3000')

            # By default WebUI simple http server listens on 8080
            origins.add('http://localhost:8080')
            origins.add('http://127.0.0.1:8080')

            if public_api_url:
                # Public API URL
                origins.add(public_api_url)

            if origin:
                if '*' in origins:
                    origin_allowed = '*'
                else:
                    # See http://www.w3.org/TR/cors/#access-control-allow-origin-response-header
                    origin_allowed = origin if origin in origins else 'null'
            else:
                origin_allowed = list(origins)[0]

            methods_allowed = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
            request_headers_allowed = ['Content-Type', 'Authorization', HEADER_ATTRIBUTE_NAME,
                                       HEADER_API_KEY_ATTRIBUTE_NAME, REQUEST_ID_HEADER]
            response_headers_allowed = ['Content-Type', 'X-Limit', 'X-Total-Count',
                                        REQUEST_ID_HEADER]

            headers['Access-Control-Allow-Origin'] = origin_allowed
            headers['Access-Control-Allow-Methods'] = ','.join(methods_allowed)
            headers['Access-Control-Allow-Headers'] = ','.join(request_headers_allowed)
            headers['Access-Control-Expose-Headers'] = ','.join(response_headers_allowed)

            return start_response(status, headers._items, exc_info)

        try:
            return self.app(environ, custom_start_response)
        except NotFoundException:
            if request.method != 'options':
                raise

            return Response()(environ, custom_start_response)


class RequestIDMiddleware(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        request = Request(environ)

        if not request.headers.get(REQUEST_ID_HEADER, None):
            req_id = str(uuid.uuid4())
            request.headers[REQUEST_ID_HEADER] = req_id

        def custom_start_response(status, headers, exc_info=None):
            headers = ResponseHeaders(headers)

            req_id_header = request.headers.get(REQUEST_ID_HEADER, None)
            if req_id_header:
                headers[REQUEST_ID_HEADER] = req_id_header

            return start_response(status, headers._items, exc_info)

        return self.app(environ, custom_start_response)


class LoggingMiddleware(object):
    """
    Logs all incoming requests and outgoing responses
    """

    def __init__(self, app, router):
        self.app = app
        self.router = router

    def __call__(self, environ, start_response):
        start_time = clock()
        status_code = []
        content_length = []

        request = Request(environ)

        # Log the incoming request
        values = {
            'method': request.method,
            'path': request.path,
            'remote_addr': request.remote_addr,
            'query': request.GET.dict_of_lists(),
            'request_id': request.headers.get(REQUEST_ID_HEADER, None)
        }

        LOG.info('%(request_id)s - %(method)s %(path)s with query=%(query)s' %
                 values, extra=values)

        def custom_start_response(status, headers, exc_info=None):
            status_code.append(int(status.split(' ')[0]))

            for name, value in headers:
                if name.lower() == 'content-length':
                    content_length.append(int(value))
                    break

            return start_response(status, headers, exc_info)

        retval = self.app(environ, custom_start_response)

        # Log the incoming request
        values = {
            'method': request.method,
            'path': request.path,
            'remote_addr': request.remote_addr,
            'status': status_code[0],
            'runtime': float("{0:.3f}".format((clock() - start_time) * 10**3)),
            'content_length': content_length[0] if content_length else len(b''.join(retval)),
            'request_id': request.headers.get(REQUEST_ID_HEADER, None)
        }

        endpoint, path_vars = self.router.match(request)

        if endpoint.get('x-log-result', True):
            values['result'] = retval[0]
            log_msg = '%(request_id)s - %(status)s %(content_length)s %(runtime)sms\n%(result)s'\
                      % values
        else:
            log_msg = '%(request_id)s - %(status)s %(content_length)s %(runtime)sms' % values

        LOG.info(log_msg, extra=values)

        return retval


class Router(object):
    def __init__(self, arguments=None, debug=False, auth=True):
        self.debug = debug
        self.auth = auth

        self.arguments = arguments or {}

        self.spec = {}
        self.spec_resolver = None
        self.routes = routes.Mapper()

    def add_spec(self, spec, default=True):
        info = spec.get('info', {})
        LOG.debug('Adding API: %s %s', info.get('title', 'untitled'), info.get('version', '0.0.0'))

        if not self.spec:
            self.spec = spec
        else:
            self.spec['paths'].update(spec['paths'])
            self.spec['definitions'].update(spec['definitions'])

        self.spec_resolver = validate_spec(copy.deepcopy(self.spec))

        for (path, methods) in six.iteritems(spec['paths']):
            for (method, endpoint) in six.iteritems(methods):
                conditions = {
                    'method': [method.upper()]
                }

                connect_kw = {}
                if 'x-requirements' in endpoint:
                    connect_kw['requirements'] = endpoint['x-requirements']

                m = self.routes.submapper(_api_path=path, _api_method=method, conditions=conditions)
                m.connect(None, spec.get('basePath', '') + path, **connect_kw)
                if default:
                    m.connect(None, path, **connect_kw)

        for route in sorted(self.routes.matchlist, key=lambda r: r.routepath):
            LOG.debug('Route registered: %+6s %s', route.conditions['method'][0], route.routepath)

    def match(self, req):
        path = req.path

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

        path = path_vars.pop('_api_path')
        method = path_vars.pop('_api_method')
        endpoint = self.spec['paths'][path][method]

        return endpoint, path_vars

    def __call__(self, req):
        """Invoke router as a view."""
        endpoint, path_vars = self.match(req)

        context = copy.copy(getattr(self, 'mock_context', {}))

        # Handle security
        if 'security' in endpoint:
            security = endpoint.get('security')
        else:
            security = self.spec.get('security', [])

        if self.auth and security:
            try:
                auth_resp = None
                security_definitions = self.spec.get('securityDefinitions', {})
                for statement in security:
                    declaration, options = statement.copy().popitem()
                    definition = security_definitions[declaration]

                    if definition['type'] == 'apiKey':
                        if definition['in'] == 'header':
                            token = req.headers.get(definition['name'])
                        elif definition['in'] == 'query':
                            token = req.GET.get(definition['name'])
                        else:
                            token = None

                        if token:
                            if auth_resp:
                                raise auth_exc.MultipleAuthSourcesError(
                                    'Only one of Token or API key expected.')

                            auth_func = op_resolver(definition['x-operationId'])
                            auth_resp = auth_func(token)

                            context['user'] = User.get_by_name(auth_resp.user)

                if 'user' not in context:
                    raise auth_exc.NoAuthSourceProvidedError('One of Token or API key required.')
            except (auth_exc.NoAuthSourceProvidedError,
                    auth_exc.MultipleAuthSourcesError) as e:
                LOG.error(str(e))
                return abort_unauthorized(str(e))
            except auth_exc.TokenNotProvidedError as e:
                LOG.exception('Token is not provided.')
                return abort_unauthorized(str(e))
            except auth_exc.TokenNotFoundError as e:
                LOG.exception('Token is not found.')
                return abort_unauthorized(str(e))
            except auth_exc.TokenExpiredError as e:
                LOG.exception('Token has expired.')
                return abort_unauthorized(str(e))
            except auth_exc.ApiKeyNotProvidedError as e:
                LOG.exception('API key is not provided.')
                return abort_unauthorized(str(e))
            except auth_exc.ApiKeyNotFoundError as e:
                LOG.exception('API key is not found.')
                return abort_unauthorized(str(e))
            except auth_exc.ApiKeyDisabledError as e:
                LOG.exception('API key is disabled.')
                return abort_unauthorized(str(e))

        if cfg.CONF.rbac.enable:
            user_db = context['user']

            permission_type = endpoint.get('x-permissions', None)
            if permission_type:
                resolver = resolvers.get_resolver_for_permission_type(permission_type)
                has_permission = resolver.user_has_permission(user_db, permission_type)

                if not has_permission:
                    raise rbac_exc.ResourceTypeAccessDeniedError(user_db,
                                                                 permission_type)

        # Collect parameters
        kw = {}
        for param in endpoint.get('parameters', []) + endpoint.get('x-parameters', []):
            name = param['name']
            argument_name = param.get('x-as', None) or name
            type = param['in']
            required = param.get('required', False)
            default = param.get('default', None)

            if type == 'query':
                kw[argument_name] = req.GET.get(name, default)
            elif type == 'path':
                kw[argument_name] = path_vars[name]
            elif type == 'header':
                kw[argument_name] = req.headers.get(name, default)
            elif type == 'body':
                if req.body:
                    content_type = req.headers.get('Content-Type', 'application/json')
                    content_type = parse_content_type_header(content_type=content_type)[0]
                    schema = param['schema']

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
                        detail = 'Failed to parse request body: %s' % str(e)
                        raise exc.HTTPBadRequest(detail=detail)

                    try:
                        CustomValidator(schema, resolver=self.spec_resolver).validate(data)
                    except (jsonschema.ValidationError, ValueError) as e:
                        raise exc.HTTPBadRequest(detail=e.message,
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
                            Model = op_resolver(schema['x-api-model'])
                        else:
                            Model = Body

                        kw[argument_name] = Model(**data)
                else:
                    kw[argument_name] = None
            elif type == 'formData':
                kw[argument_name] = req.POST.get(name, default)
            elif type == 'environ':
                kw[argument_name] = req.environ.get(name.upper(), default)
            elif type == 'context':
                kw[argument_name] = context.get(name, default)
            elif type == 'request':
                kw[argument_name] = getattr(req, name)

            if required and not kw[argument_name]:
                detail = 'Required parameter "%s" is missing' % name
                raise exc.HTTPBadRequest(detail=detail)

        # Call the controller
        func = op_resolver(endpoint['operationId'])
        resp = func(**kw)

        # Handle response
        if resp is not None:
            if not hasattr(resp, '__call__'):
                resp = Response(json=resp)
        else:
            resp = Response()

        responses = endpoint.get('responses', {})
        response_spec = responses.get(str(resp.status_code), responses.get('default', None))

        if response_spec and 'schema' in response_spec:
            try:
                validator = CustomValidator(response_spec['schema'], resolver=self.spec_resolver)
                validator.validate(resp.json)
            except (jsonschema.ValidationError, ValueError):
                LOG.exception('Response validation failed.')
                resp.headers.add('Warning', '199 OpenAPI "Response validation failed"')

        return resp

    def as_wsgi(self, environ, start_response):
        """Invoke router as an wsgi application."""
        req = Request(environ)
        resp = self(req)
        return resp(environ, start_response)
