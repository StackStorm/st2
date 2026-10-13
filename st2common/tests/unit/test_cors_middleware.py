# Copyright 2026 The StackStorm Authors.
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

import unittest
from oslo_config import cfg
from webob.headers import ResponseHeaders

from st2common import config as st2common_config
from st2common.middleware.cors import CorsMiddleware

__all__ = ["CorsMiddlewareTestCase"]


class CorsMiddlewareTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        st2common_config.register_opts(ignore_errors=True)

    def _call_middleware(
        self, environ, app_status="200 OK", app_headers=None, app_body=b"OK"
    ):
        def dummy_app(env, start_response):
            headers = list(app_headers or [])
            start_response(app_status, headers)
            return [app_body]

        middleware = CorsMiddleware(dummy_app)
        captured = {}

        def dummy_start_response(status, headers, exc_info=None):
            captured["status"] = status
            captured["headers"] = ResponseHeaders(headers)

        body_iterable = middleware(environ, dummy_start_response)
        body = b"".join(body_iterable) if body_iterable else b""
        return {
            "status": captured.get("status"),
            "headers": captured.get("headers", ResponseHeaders()),
            "body": body,
        }

    def test_explicit_whitelisted_origin_allows_credentials(self):
        cfg.CONF.set_override("allow_origin", ["http://127.0.0.1:3000"], "api")
        environ = {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/v1/actions",
            "HTTP_ORIGIN": "http://127.0.0.1:3000",
        }
        res = self._call_middleware(environ)
        headers = res["headers"]
        self.assertEqual(
            headers.get("Access-Control-Allow-Origin"), "http://127.0.0.1:3000"
        )
        self.assertEqual(headers.get("Access-Control-Allow-Credentials"), "true")
        self.assertEqual(headers.get("Vary"), "Origin")

    def test_multiple_whitelisted_origins(self):
        allowed = [
            "http://app1.internal:3000",
            "https://app2.internal:8443",
            "http://app3.corp",
        ]
        cfg.CONF.set_override("allow_origin", allowed, "api")

        for origin in allowed:
            environ = {
                "REQUEST_METHOD": "GET",
                "PATH_INFO": "/v1/actions",
                "HTTP_ORIGIN": origin,
            }
            res = self._call_middleware(environ)
            headers = res["headers"]
            self.assertEqual(headers.get("Access-Control-Allow-Origin"), origin)
            self.assertEqual(headers.get("Access-Control-Allow-Credentials"), "true")
            self.assertEqual(headers.get("Vary"), "Origin")

    def test_wildcard_origin_never_allows_credentials(self):
        cfg.CONF.set_override("allow_origin", ["*"], "api")

        test_origins = [
            "http://evil.com",
            "https://subdomain.attacker.org:8080",
            "null",
            "file://",
            "https://attacker.evil.com/path",
        ]

        for origin in test_origins:
            environ = {
                "REQUEST_METHOD": "GET",
                "PATH_INFO": "/v1/actions",
                "HTTP_ORIGIN": origin,
            }
            res = self._call_middleware(environ)
            headers = res["headers"]
            # Must return wildcard, NEVER reflect the untrusted origin
            self.assertEqual(headers.get("Access-Control-Allow-Origin"), "*")
            # Must NEVER include Access-Control-Allow-Credentials with wildcard
            self.assertNotIn("Access-Control-Allow-Credentials", headers)

    def test_wildcard_origin_without_origin_header(self):
        cfg.CONF.set_override("allow_origin", ["*"], "api")
        environ = {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/v1/actions",
        }
        res = self._call_middleware(environ)
        headers = res["headers"]
        self.assertEqual(headers.get("Access-Control-Allow-Origin"), "*")
        self.assertNotIn("Access-Control-Allow-Credentials", headers)

    def test_wildcard_and_specific_origin_combination(self):
        cfg.CONF.set_override("allow_origin", ["http://trusted.com", "*"], "api")

        # Explicitly trusted origin gets credentials
        environ_trusted = {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/v1/actions",
            "HTTP_ORIGIN": "http://trusted.com",
        }
        res_trusted = self._call_middleware(environ_trusted)
        headers_trusted = res_trusted["headers"]
        self.assertEqual(
            headers_trusted.get("Access-Control-Allow-Origin"),
            "http://trusted.com",
        )
        self.assertEqual(
            headers_trusted.get("Access-Control-Allow-Credentials"), "true"
        )

        # Untrusted origin falls back to wildcard without credentials
        environ_untrusted = {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/v1/actions",
            "HTTP_ORIGIN": "http://evil.com",
        }
        res_untrusted = self._call_middleware(environ_untrusted)
        headers_untrusted = res_untrusted["headers"]
        self.assertEqual(headers_untrusted.get("Access-Control-Allow-Origin"), "*")
        self.assertNotIn("Access-Control-Allow-Credentials", headers_untrusted)

    def test_disallowed_origin_does_not_allow_credentials(self):
        cfg.CONF.set_override("allow_origin", ["http://trusted.com"], "api")
        environ = {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/v1/actions",
            "HTTP_ORIGIN": "http://evil.com",
        }
        res = self._call_middleware(environ)
        headers = res["headers"]
        # Fallback to configured origin so browser fails origin match
        self.assertEqual(
            headers.get("Access-Control-Allow-Origin"), "http://trusted.com"
        )
        # Disallowed origin must NEVER receive credentials
        self.assertNotIn("Access-Control-Allow-Credentials", headers)
        self.assertEqual(headers.get("Vary"), "Origin")

    def test_origin_subdomain_or_prefix_mismatch_rejected(self):
        cfg.CONF.set_override("allow_origin", ["http://trusted.com"], "api")
        prefix_attacks = [
            "http://trusted.com.evil.com",
            "http://evil-trusted.com",
            "http://not-trusted.com",
        ]
        for attack_origin in prefix_attacks:
            environ = {
                "REQUEST_METHOD": "GET",
                "PATH_INFO": "/v1/actions",
                "HTTP_ORIGIN": attack_origin,
            }
            res = self._call_middleware(environ)
            headers = res["headers"]
            self.assertEqual(
                headers.get("Access-Control-Allow-Origin"), "http://trusted.com"
            )
            self.assertNotIn("Access-Control-Allow-Credentials", headers)

    def test_origin_port_or_scheme_mismatch_rejected(self):
        cfg.CONF.set_override("allow_origin", ["http://trusted.com:9101"], "api")
        mismatches = [
            "https://trusted.com:9101",  # Scheme mismatch
            "http://trusted.com:9102",  # Port mismatch
            "http://trusted.com",  # Default port mismatch
        ]
        for mismatch_origin in mismatches:
            environ = {
                "REQUEST_METHOD": "GET",
                "PATH_INFO": "/v1/actions",
                "HTTP_ORIGIN": mismatch_origin,
            }
            res = self._call_middleware(environ)
            headers = res["headers"]
            self.assertEqual(
                headers.get("Access-Control-Allow-Origin"),
                "http://trusted.com:9101",
            )
            self.assertNotIn("Access-Control-Allow-Credentials", headers)

    def test_null_origin_does_not_allow_credentials(self):
        cfg.CONF.set_override("allow_origin", ["http://trusted.com"], "api")
        environ = {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/v1/actions",
            "HTTP_ORIGIN": "null",
        }
        res = self._call_middleware(environ)
        headers = res["headers"]
        self.assertEqual(
            headers.get("Access-Control-Allow-Origin"), "http://trusted.com"
        )
        self.assertNotIn("Access-Control-Allow-Credentials", headers)

    def test_no_origin_header_does_not_set_credentials(self):
        cfg.CONF.set_override("allow_origin", ["http://trusted.com"], "api")
        environ = {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/v1/actions",
        }
        res = self._call_middleware(environ)
        headers = res["headers"]
        self.assertEqual(
            headers.get("Access-Control-Allow-Origin"), "http://trusted.com"
        )
        self.assertNotIn("Access-Control-Allow-Credentials", headers)

    def test_hardcoded_localhost_origins_not_injected(self):
        cfg.CONF.set_override("allow_origin", ["http://custom.example.com"], "api")

        for local_origin in [
            "http://127.0.0.1:3000",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
            "http://localhost:3000",
        ]:
            environ = {
                "REQUEST_METHOD": "GET",
                "PATH_INFO": "/v1/actions",
                "HTTP_ORIGIN": local_origin,
            }
            res = self._call_middleware(environ)
            headers = res["headers"]
            self.assertEqual(
                headers.get("Access-Control-Allow-Origin"),
                "http://custom.example.com",
            )
            self.assertNotIn("Access-Control-Allow-Credentials", headers)

    def test_public_api_url_origin_allowed_with_credentials(self):
        cfg.CONF.set_override("allow_origin", ["http://custom.example.com"], "api")
        cfg.CONF.set_override("api_url", "http://api.company.internal", "auth")

        environ = {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/v1/actions",
            "HTTP_ORIGIN": "http://api.company.internal",
        }
        res = self._call_middleware(environ)
        headers = res["headers"]
        self.assertEqual(
            headers.get("Access-Control-Allow-Origin"),
            "http://api.company.internal",
        )
        self.assertEqual(headers.get("Access-Control-Allow-Credentials"), "true")

    def test_empty_origins_configuration_handled_safely(self):
        cfg.CONF.set_override("allow_origin", [], "api")
        cfg.CONF.set_override("api_url", None, "auth")

        # With origin
        environ_with_origin = {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/v1/actions",
            "HTTP_ORIGIN": "http://some-origin.com",
        }
        res_with = self._call_middleware(environ_with_origin)
        self.assertNotIn("Access-Control-Allow-Origin", res_with["headers"])
        self.assertNotIn("Access-Control-Allow-Credentials", res_with["headers"])

        # Without origin
        environ_without_origin = {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/v1/actions",
        }
        res_without = self._call_middleware(environ_without_origin)
        self.assertNotIn("Access-Control-Allow-Origin", res_without["headers"])
        self.assertNotIn("Access-Control-Allow-Credentials", res_without["headers"])

    def test_options_preflight_for_allowed_origin(self):
        cfg.CONF.set_override("allow_origin", ["http://127.0.0.1:3000"], "api")
        environ = {
            "REQUEST_METHOD": "OPTIONS",
            "PATH_INFO": "/v1/actions",
            "HTTP_ORIGIN": "http://127.0.0.1:3000",
        }
        res = self._call_middleware(environ)
        headers = res["headers"]
        self.assertEqual(res["status"], "200 OK")
        self.assertEqual(
            headers.get("Access-Control-Allow-Origin"), "http://127.0.0.1:3000"
        )
        self.assertEqual(headers.get("Access-Control-Allow-Credentials"), "true")
        self.assertEqual(
            headers.get("Access-Control-Allow-Methods"),
            "GET,POST,PUT,DELETE,OPTIONS",
        )
        self.assertIn("Content-Type", headers.get("Access-Control-Allow-Headers", ""))
        self.assertIn("Authorization", headers.get("Access-Control-Allow-Headers", ""))
        self.assertIn("X-Auth-Token", headers.get("Access-Control-Allow-Headers", ""))
        self.assertIn("St2-Api-Key", headers.get("Access-Control-Allow-Headers", ""))
        self.assertIn("X-Request-ID", headers.get("Access-Control-Allow-Headers", ""))
        self.assertIn("X-Limit", headers.get("Access-Control-Expose-Headers", ""))
        self.assertIn("X-Total-Count", headers.get("Access-Control-Expose-Headers", ""))

    def test_options_preflight_for_wildcard_origin(self):
        cfg.CONF.set_override("allow_origin", ["*"], "api")
        environ = {
            "REQUEST_METHOD": "OPTIONS",
            "PATH_INFO": "/v1/actions",
            "HTTP_ORIGIN": "http://evil.com",
        }
        res = self._call_middleware(environ)
        headers = res["headers"]
        self.assertEqual(res["status"], "200 OK")
        self.assertEqual(headers.get("Access-Control-Allow-Origin"), "*")
        self.assertNotIn("Access-Control-Allow-Credentials", headers)

    def test_options_preflight_for_disallowed_origin(self):
        cfg.CONF.set_override("allow_origin", ["http://trusted.com"], "api")
        environ = {
            "REQUEST_METHOD": "OPTIONS",
            "PATH_INFO": "/v1/actions",
            "HTTP_ORIGIN": "http://evil.com",
        }
        res = self._call_middleware(environ)
        headers = res["headers"]
        self.assertEqual(res["status"], "200 OK")
        self.assertEqual(
            headers.get("Access-Control-Allow-Origin"), "http://trusted.com"
        )
        self.assertNotIn("Access-Control-Allow-Credentials", headers)

    def test_options_preflight_without_origin(self):
        cfg.CONF.set_override("allow_origin", ["http://trusted.com"], "api")
        environ = {
            "REQUEST_METHOD": "OPTIONS",
            "PATH_INFO": "/v1/actions",
        }
        res = self._call_middleware(environ)
        headers = res["headers"]
        self.assertEqual(res["status"], "200 OK")
        self.assertEqual(
            headers.get("Access-Control-Allow-Origin"), "http://trusted.com"
        )
        self.assertNotIn("Access-Control-Allow-Credentials", headers)

    def test_all_http_methods_and_status_codes_preserve_body_and_status(self):
        cfg.CONF.set_override("allow_origin", ["http://trusted.com"], "api")

        test_cases = [
            ("GET", "200 OK", b'{"status": "ok"}'),
            ("POST", "201 Created", b'{"id": "123"}'),
            ("DELETE", "204 No Content", b""),
            ("PUT", "400 Bad Request", b'{"fault": "invalid"}'),
            ("GET", "401 Unauthorized", b'{"fault": "unauthorized"}'),
            ("GET", "403 Forbidden", b'{"fault": "forbidden"}'),
            ("GET", "404 Not Found", b'{"fault": "not found"}'),
            ("POST", "500 Internal Server Error", b'{"fault": "server error"}'),
            ("PATCH", "200 OK", b'{"patched": true}'),
            ("HEAD", "200 OK", b""),
        ]

        for method, status_str, body_bytes in test_cases:
            environ = {
                "REQUEST_METHOD": method,
                "PATH_INFO": "/v1/actions",
                "HTTP_ORIGIN": "http://trusted.com",
            }
            res = self._call_middleware(
                environ,
                app_status=status_str,
                app_headers=[("Content-Type", "application/json")],
                app_body=body_bytes,
            )
            self.assertEqual(res["status"], status_str)
            self.assertEqual(res["body"], body_bytes)
            self.assertEqual(
                res["headers"].get("Access-Control-Allow-Origin"),
                "http://trusted.com",
            )
            self.assertEqual(
                res["headers"].get("Access-Control-Allow-Credentials"), "true"
            )

    def test_custom_application_response_headers_preserved(self):
        cfg.CONF.set_override("allow_origin", ["http://trusted.com"], "api")
        environ = {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/v1/actions",
            "HTTP_ORIGIN": "http://trusted.com",
        }
        custom_headers = [
            ("X-Custom-Trace-ID", "trace-98765"),
            ("Content-Security-Policy", "default-src 'self'"),
            ("Strict-Transport-Security", "max-age=31536000; includeSubDomains"),
        ]
        res = self._call_middleware(environ, app_headers=custom_headers)
        headers = res["headers"]

        # Custom headers preserved
        self.assertEqual(headers.get("X-Custom-Trace-ID"), "trace-98765")
        self.assertEqual(headers.get("Content-Security-Policy"), "default-src 'self'")
        self.assertEqual(
            headers.get("Strict-Transport-Security"),
            "max-age=31536000; includeSubDomains",
        )

        # CORS headers also attached
        self.assertEqual(
            headers.get("Access-Control-Allow-Origin"), "http://trusted.com"
        )
        self.assertEqual(headers.get("Access-Control-Allow-Credentials"), "true")

    def test_vary_header_handling(self):
        cfg.CONF.set_override("allow_origin", ["http://trusted.com"], "api")
        environ = {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/v1/actions",
            "HTTP_ORIGIN": "http://trusted.com",
        }

        # 1. No existing Vary header -> sets "Origin"
        res1 = self._call_middleware(environ)
        self.assertEqual(res1["headers"].get("Vary"), "Origin")

        # 2. Existing Vary header with other tokens -> appends ", Origin"
        res2 = self._call_middleware(
            environ, app_headers=[("Vary", "Accept-Encoding, User-Agent")]
        )
        self.assertEqual(
            res2["headers"].get("Vary"), "Accept-Encoding, User-Agent, Origin"
        )

        # 3. Existing Vary header already containing Origin (case-insensitive) -> untouched
        res3 = self._call_middleware(
            environ, app_headers=[("Vary", "Accept-Encoding, origin")]
        )
        self.assertEqual(res3["headers"].get("Vary"), "Accept-Encoding, origin")

        # 4. Existing Vary header containing * -> untouched
        res4 = self._call_middleware(environ, app_headers=[("Vary", "*")])
        self.assertEqual(res4["headers"].get("Vary"), "*")

        # 5. Wildcard origin config does not add Vary
        cfg.CONF.set_override("allow_origin", ["*"], "api")
        res5 = self._call_middleware(environ, app_headers=[("Vary", "Accept-Encoding")])
        self.assertEqual(res5["headers"].get("Vary"), "Accept-Encoding")

    def test_whitespace_in_configured_origins_handled(self):
        cfg.CONF.set_override(
            "allow_origin", ["  http://trusted1.com  ", " http://trusted2.com "], "api"
        )
        cfg.CONF.set_override("api_url", "  http://public-api.corp  ", "auth")

        for origin in [
            "http://trusted1.com",
            "http://trusted2.com",
            "http://public-api.corp",
        ]:
            environ = {
                "REQUEST_METHOD": "GET",
                "PATH_INFO": "/v1/actions",
                "HTTP_ORIGIN": origin,
            }
            res = self._call_middleware(environ)
            headers = res["headers"]
            self.assertEqual(headers.get("Access-Control-Allow-Origin"), origin)
            self.assertEqual(headers.get("Access-Control-Allow-Credentials"), "true")
