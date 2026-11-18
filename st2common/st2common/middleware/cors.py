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
from oslo_config import cfg
from webob.headers import ResponseHeaders

from st2common.constants.api import REQUEST_ID_HEADER
from st2common.constants.auth import HEADER_ATTRIBUTE_NAME
from st2common.constants.auth import HEADER_API_KEY_ATTRIBUTE_NAME
from st2common.util.types import OrderedSet
from st2common.router import Request
from st2common.router import Response


class CorsMiddleware(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        # The middleware sets a number of headers that helps prevent a range of attacks in browser
        # environment. It also handles OPTIONS requests used by browser as pre-flight check before
        # the potentially insecure request is made. An absence of this headers on the response will
        # prevent the error from ever reaching the JS layer of client-side code making it impossible
        # to process the response or provide a human-friendly error message. Order is not important
        # as long at this condition is met and headers not get overridden by another middleware
        # higher up the call stack.
        request = Request(environ)

        def custom_start_response(status, headers, exc_info=None):
            headers = ResponseHeaders(headers)

            origin = request.headers.get("Origin")
            raw_origins = cfg.CONF.api.allow_origin or []
            origins = OrderedSet(
                [o.strip() for o in raw_origins if isinstance(o, str) and o.strip()]
            )

            # Build a list of the default allowed origins
            public_api_url = cfg.CONF.auth.api_url

            if (
                public_api_url
                and isinstance(public_api_url, str)
                and public_api_url.strip()
            ):
                # Public API URL
                origins.add(public_api_url.strip())

            origins = list(origins)

            origin_allowed = None
            allow_credentials = False
            vary_origin = False

            if origin:
                if origin in origins and origin != "*":
                    origin_allowed = origin
                    allow_credentials = True
                    vary_origin = True
                elif "*" in origins:
                    origin_allowed = "*"
                    allow_credentials = False
                elif origins:
                    # Origin is not allowed; return first configured origin (per commit 66605b7b)
                    # so browser CORS check rejects it, while not enabling credentials.
                    origin_allowed = origins[0]
                    allow_credentials = False
                    vary_origin = True
            elif origins:
                # No Origin header was provided (e.g. non-browser client / direct request).
                if "*" in origins:
                    origin_allowed = "*"
                else:
                    origin_allowed = origins[0]
                allow_credentials = False

            methods_allowed = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
            request_headers_allowed = [
                "Content-Type",
                "Authorization",
                HEADER_ATTRIBUTE_NAME,
                HEADER_API_KEY_ATTRIBUTE_NAME,
                REQUEST_ID_HEADER,
            ]
            response_headers_allowed = [
                "Content-Type",
                "X-Limit",
                "X-Total-Count",
                REQUEST_ID_HEADER,
            ]

            if origin_allowed:
                headers["Access-Control-Allow-Origin"] = origin_allowed
                if vary_origin:
                    existing_vary = headers.get("Vary")
                    if existing_vary:
                        vary_tokens = [
                            v.strip().lower() for v in existing_vary.split(",")
                        ]
                        if "origin" not in vary_tokens and "*" not in vary_tokens:
                            headers["Vary"] = "%s, Origin" % existing_vary
                    else:
                        headers["Vary"] = "Origin"

            headers["Access-Control-Allow-Methods"] = ",".join(methods_allowed)
            headers["Access-Control-Allow-Headers"] = ",".join(request_headers_allowed)

            if allow_credentials:
                headers["Access-Control-Allow-Credentials"] = "true"

            headers["Access-Control-Expose-Headers"] = ",".join(
                response_headers_allowed
            )

            return start_response(status, headers._items, exc_info)

        if request.method == "OPTIONS":
            return Response()(environ, custom_start_response)
        else:
            return self.app(environ, custom_start_response)
