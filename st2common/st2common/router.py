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
from collections import namedtuple
import six
import sys
import traceback

import jsonschema
from oslo_config import cfg
import routes
from six.moves.urllib import parse as urlparse  # pylint: disable=import-error
from swagger_spec_validator.validator20 import validate_spec
from webob import exc, Request, Response

from st2common.exceptions import rbac as rbac_exc
from st2common.exceptions import auth as auth_exc
from st2common import hooks
from st2common import log as logging
from st2common.persistence.auth import User
from st2common.rbac import resolvers
from st2common.util.jsonify import json_encode
from st2common.util.http import parse_content_type_header


LOG = logging.getLogger(__name__)


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


class ErrorHandlingMiddleware(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        try:
            try:
                resp = self.app(environ, start_response)
            except NotFoundException:
                raise exc.HTTPNotFound()
        except Exception as e:
            # Mostly hacking to avoid making changes to the hook
            State = namedtuple('State', 'response')
            Response = namedtuple('Response', 'status headers')

            state = State(
                response=Response(
                    status=getattr(e, 'code', 500),
                    headers={}
                )
            )

            if hasattr(e, 'detail') and not getattr(e, 'comment'):
                setattr(e, 'comment', getattr(e, 'detail'))

            resp = hooks.JSONErrorResponseHook().on_error(state, e)(environ, start_response)
        return resp


class Router(object):
    # For mocking during unit tests
    context = {}

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

        self.spec_resolver = validate_spec(copy.deepcopy(spec))
        self.spec = spec

        for (path, methods) in six.iteritems(spec['paths']):
            for (method, endpoint) in six.iteritems(methods):
                conditions = {
                    'method': [method.upper()]
                }

                connect_kw = {}
                if 'x-requirements' in endpoint:
                    connect_kw['requirements'] = endpoint['x-requirements']

                m = self.routes.submapper(_api_path=path, _api_method=method, conditions=conditions)
                m.connect(None, self.spec.get('basePath', '') + path, **connect_kw)
                if default:
                    m.connect(None, path, **connect_kw)

        for route in self.routes.matchlist:
            LOG.debug('Route registered: %s %s', route.routepath, route.conditions)

    def __call__(self, req):
        """Invoke router as a view."""
        LOG.info('%s %s', req.method, req.path)
        match = self.routes.match(req.path, req.environ)

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
        context = copy.copy(self.context)

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
                resp = Response(json_encode(resp), content_type='application/json')
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
