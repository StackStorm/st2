# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import

import traceback

import six
from mongoengine import ValidationError

from st2common.exceptions import db as db_exceptions
from st2common.exceptions import rbac as rbac_exceptions
from st2common.exceptions.apivalidation import ValueValidationException
from st2common import log as logging
from st2common.router import exc, Response, NotFoundException
from st2common.util.debugging import is_enabled as is_debugging_enabled
from st2common.util.jsonify import json_encode


LOG = logging.getLogger(__name__)


class ErrorHandlingMiddleware(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        # The middleware intercepts and handles all the errors happening down the call stack by
        # converting them to valid HTTP responses with semantically meaningful status codes and
        # predefined response structure (`{"faultstring": "..."}`). The earlier in the call stack is
        # going to be run, the less unhandled errors could slip to the wsgi layer. Keep in mind that
        # the middleware doesn't receive the headers that has been set down the call stack which
        # means that things like CorsMiddleware and RequestIDMiddleware should be highier up the
        # call stack to also apply to error responses.
        try:
            try:
                return self.app(environ, start_response)
            except NotFoundException:
                raise exc.HTTPNotFound()
        except Exception as e:
            status = getattr(e, "code", exc.HTTPInternalServerError.code)

            if hasattr(e, "detail") and not getattr(e, "comment"):
                setattr(e, "comment", getattr(e, "detail"))

            if hasattr(e, "body") and isinstance(getattr(e, "body", None), dict):
                body = getattr(e, "body", None)
            else:
                body = {}

            if isinstance(e, exc.HTTPException):
                status_code = status
                message = six.text_type(e)
            elif isinstance(e, db_exceptions.StackStormDBObjectNotFoundError):
                status_code = exc.HTTPNotFound.code
                message = six.text_type(e)
            elif isinstance(e, db_exceptions.StackStormDBObjectConflictError):
                status_code = exc.HTTPConflict.code
                message = six.text_type(e)
                body["conflict-id"] = getattr(e, "conflict_id", None)
            elif isinstance(e, rbac_exceptions.AccessDeniedError):
                status_code = exc.HTTPForbidden.code
                message = six.text_type(e)
            elif isinstance(e, (ValueValidationException, ValueError, ValidationError)):
                status_code = exc.HTTPBadRequest.code
                message = getattr(e, "message", six.text_type(e))
            else:
                status_code = exc.HTTPInternalServerError.code
                message = "Internal Server Error"

            # Log the error
            is_internal_server_error = status_code == exc.HTTPInternalServerError.code
            error_msg = getattr(e, "comment", six.text_type(e))
            extra = {
                "exception_class": e.__class__.__name__,
                "exception_message": six.text_type(e),
                "exception_data": e.__dict__,
            }

            if is_internal_server_error:
                LOG.exception("API call failed: %s", error_msg, extra=extra)
            else:
                LOG.debug("API call failed: %s", error_msg, extra=extra)

                if is_debugging_enabled():
                    LOG.debug(traceback.format_exc())

            body["faultstring"] = message

            response_body = json_encode(body)

            headers = {
                "Content-Type": "application/json",
                # NOTE: We need to use the length of the byte string here otherwise it won't
                # work correctly when returning an unicode response - here we would measure number
                # of characters instead of actual byte length.
                # Another option would also be to not set it here and let webob set it when sending
                # the response.
                "Content-Length": str(len(response_body.encode("utf-8"))),
            }

            resp = Response(response_body, status=status_code, headers=headers)

            return resp(environ, start_response)
