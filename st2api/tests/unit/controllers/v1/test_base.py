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

import webob
from oslo_config import cfg
from webob.request import Request

from st2common.router import Router

from st2tests.api import FunctionalTest


class TestBase(FunctionalTest):
    def test_defaults(self):
        response = self.app.get("/")
        self.assertEqual(response.status_int, 200)
        self.assertEqual(
            response.headers["Access-Control-Allow-Origin"], "http://127.0.0.1:3000"
        )
        self.assertEqual(
            response.headers["Access-Control-Allow-Methods"],
            "GET,POST,PUT,DELETE,OPTIONS",
        )
        self.assertEqual(
            response.headers["Access-Control-Allow-Headers"],
            "Content-Type,Authorization,X-Auth-Token,St2-Api-Key,X-Request-ID",
        )
        self.assertEqual(
            response.headers["Access-Control-Expose-Headers"],
            "Content-Type,X-Limit,X-Total-Count,X-Request-ID",
        )

    def test_origin(self):
        response = self.app.get("/", headers={"origin": "http://127.0.0.1:3000"})
        self.assertEqual(response.status_int, 200)
        self.assertEqual(
            response.headers["Access-Control-Allow-Origin"], "http://127.0.0.1:3000"
        )

    def test_additional_origin(self):
        response = self.app.get("/", headers={"origin": "http://dev"})
        self.assertEqual(response.status_int, 200)
        self.assertEqual(response.headers["Access-Control-Allow-Origin"], "http://dev")

    def test_wrong_origin(self):
        # Invalid origin  (not specified in the config), we return first allowed origin specified
        # in the config
        response = self.app.get("/", headers={"origin": "http://xss"})
        self.assertEqual(response.status_int, 200)
        self.assertEqual(
            response.headers.get("Access-Control-Allow-Origin"), "http://127.0.0.1:3000"
        )

        invalid_origins = [
            "http://",
            "https://",
            "https://www.example.com",
            "null",
            "*",
        ]

        for origin in invalid_origins:
            response = self.app.get("/", headers={"origin": origin})
            self.assertEqual(response.status_int, 200)
            self.assertEqual(
                response.headers.get("Access-Control-Allow-Origin"),
                "http://127.0.0.1:3000",
            )

    def test_wildcard_origin(self):
        try:
            cfg.CONF.set_override("allow_origin", ["*"], "api")
            response = self.app.get("/", headers={"origin": "http://xss"})
        finally:
            cfg.CONF.clear_override("allow_origin", "api")
        self.assertEqual(response.status_int, 200)
        self.assertEqual(response.headers["Access-Control-Allow-Origin"], "http://xss")

    def test_valid_status_code_is_returned_on_invalid_path(self):
        # TypeError: get_all() takes exactly 1 argument (2 given)
        resp = self.app.get(
            "/v1/executions/577f775b0640fd1451f2030b/re_run", expect_errors=True
        )
        self.assertEqual(resp.status_int, 404)

        # get_one() takes exactly 2 arguments (4 given)
        resp = self.app.get(
            "/v1/executions/577f775b0640fd1451f2030b/re_run/a/b", expect_errors=True
        )
        self.assertEqual(resp.status_int, 404)

    def test_router_invalid_url_path_friendly_error(self):
        # NOTE: We intentionally don't use sp.app.get here since that goes through the webtest
        # layer which manipulates the path which means we won't be testing what we actually want
        # to test (an edge case). To test the edge case correctly, we need to manually call router
        # with specifically crafted data.
        router = Router()
        request = Request(environ={"PATH_INFO": "/v1/rules/好的".encode("utf-8")})

        expected_msg = "URL likely contains invalid or incorrectly URL encoded values"
        self.assertRaisesRegexp(
            webob.exc.HTTPBadRequest, expected_msg, router.match, request
        )
