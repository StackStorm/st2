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
import uuid

from webob.headers import ResponseHeaders

from st2common.constants.api import REQUEST_ID_HEADER
from st2common.router import Request


class RequestIDMiddleware(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        # The middleware adds unique `X-Request-ID` header on the requests that don't have it and
        # modifies the responses to have the same exact header as their request. The middleware
        # helps us better track relation between request and response in places where it might not
        # be immediately obvious (like logs for example). In general, you want to place this header
        # as soon as possible to ensure it's present by the time it's needed. Certainly before
        # LoggingMiddleware which relies on this header.
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
