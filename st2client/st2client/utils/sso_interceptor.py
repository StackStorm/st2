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
#
import json
import logging
from threading import Thread
import time
from urllib.parse import urlparse, parse_qs
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer

from st2client.utils.crypto import symmetric_decrypt

LOG = logging.getLogger(__name__)


# Implements a local HTTP server used to intercept calls from/to SSO endpoints :)
# via callback URLs
class SSOInterceptorProxy:

    thread = None
    server = None
    # Identifier to be used to access the SSO proxy (e.g. localhost:31283/<id>)
    url_id = uuid.uuid4()
    # where should the proxy redirect to upon hitting it?
    sso_url = None
    # key that is used to decrypt the response
    key = None
    # token object to receive the token once it's avaiable!
    token = None

    def __init__(self, key, sso_port):

        self.server = HTTPServer(("localhost", sso_port), createSSOProxyHandler(self))
        self.key = key

        LOG.debug(
            "Initialized SSO interceptor proxy at port %d and url id %s, SSO URL is still pending",
            self.server.server_port,
            self.url_id,
        )

        self.thread = Thread(target=self.server.serve_forever)
        self.thread.setDaemon(True)
        self.thread.start()

    def set_sso_url(self, sso_url):
        self.sso_url = sso_url
        LOG.debug("SSO URL set to [%s]", sso_url)

    def get_proxy_url(self):
        return "http://localhost:%d/%s" % (self.server.server_port, self.url_id)

    def get_callback_url(self):
        return "http://localhost:%d/callback" % (self.server.server_port)

    def callback_received(self, token):
        LOG.debug("Callback received and intercepted, token is provided :)")
        self.token = token

    def get_token(self, timeout=90):
        LOG.debug(
            "Waiting for token to be received from SSO flow.. will timeout after [%s]s",
            timeout,
        )
        timeout_at = time.time() + timeout
        while time.time() < timeout_at:
            if self.token is not None:
                return self.token
            time.sleep(0.5)

        raise TimeoutError(
            "Token was not received from SSO flow before the timeout of %ss" % timeout
        )


def createSSOProxyHandler(interceptor: SSOInterceptorProxy):
    class SSOProxyServer(BaseHTTPRequestHandler):
        def do_GET(self):

            o = urlparse(self.path)
            qs = parse_qs(o.query)

            try:

                if o.path == "/callback":
                    self._handle_callback(qs.get("response", [None])[0])
                elif o.path == "/success":
                    self._handle_success()
                elif o.path == "/%s" % interceptor.url_id:
                    self._handle_sso_login()
                else:
                    self._handle_unexpected_request()

            except ValueError as e:
                self.send_error(400, explain="Invalid parameter: %s" % str(e))
            except Exception as e:
                LOG.debug("Unexpected internal server error! %e", e)
                self.send_error(500, explain="Unexpected error!" % str(e))

            return True

        # This request is not expected by the sso proxy
        def _handle_unexpected_request(self):
            self.send_error(404, explain="The selected URL does not exist!")
            self.end_headers()

        # This request is to redirect the user to the proper sso place
        # -- can only be achieve with the proper key :)
        def _handle_sso_login(self):
            LOG.debug("Intercepting SSO begin flow from the user")
            self.send_response(307)
            self.send_header("Location", interceptor.sso_url)
            self.end_headers()

        # This request should have all the callback data we are expecting
        # -- this means an encrypted key to be decrypted and used by the CLI :)
        def _handle_callback(self, response):
            LOG.debug("Intercepting SSO callback response!")

            if response is None:
                raise ValueError(
                    "Expected 'response' field with encrypted key in callback!"
                )

            token = None
            try:
                token = symmetric_decrypt(interceptor.key, response.encode("utf-8"))
                token_json = json.loads(token)
                LOG.debug(
                    "Successful SSO login for user %s, redirecting to successful page!",
                    token_json.get("user", None),
                )
            except:
                LOG.debug("Could not understand the SSO callback response!")
                raise ValueError(
                    "Could not understand the incoming SSO callback response"
                )

            interceptor.callback_received(token)
            self.send_response(302)
            self.send_header("Location", "/success")
            self.end_headers()

            # self.wfile.close()

        def _handle_success(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(
                bytes(
                    """
                <html><head><title>SSO Login Successful</title></head>
                <body style='font: 16px arial; line-height: 30px;arial'>
                <div style='margin: auto; white-space: nowrap; display: table;
                    border: 1px solid #cccccc; padding: 18px; margin-top: 20px'>
                    <div><b>Successfully logged into StackStorm using SSO!</b></div>
                    <div>Please check your terminal</div>
                    <div>You may now close this page</div>
                </div
                <body>
                </html>
                """,
                    "utf-8",
                )
            )

        def log_message(self, format, *args):
            LOG.debug("%s " + format, "SSO Proxy: ", *args)
            return

    return SSOProxyServer
