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

import ast
import copy
import uuid

import requests
from requests.auth import HTTPBasicAuth
from oslo_config import cfg
from six.moves.urllib import parse as urlparse  # pylint: disable=import-error

from st2common.runners.base import ActionRunner
from st2common.runners.base import get_metadata as get_runner_metadata
from st2common import __version__ as st2_version
from st2common import log as logging
from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED
from st2common.constants.action import LIVEACTION_STATUS_FAILED
from st2common.constants.action import LIVEACTION_STATUS_TIMED_OUT
from st2common.util.jsonify import json_decode
from st2common.util.jsonify import json_encode
import six
from six.moves import range

__all__ = ["HttpRunner", "HTTPClient", "get_runner", "get_metadata"]

LOG = logging.getLogger(__name__)
SUCCESS_STATUS_CODES = [code for code in range(200, 207)]

# Lookup constants for runner params
RUNNER_ON_BEHALF_USER = "user"
RUNNER_URL = "url"
RUNNER_HEADERS = "headers"  # Debatable whether this should be action params.
RUNNER_COOKIES = "cookies"
RUNNER_ALLOW_REDIRECTS = "allow_redirects"
RUNNER_HTTP_PROXY = "http_proxy"
RUNNER_HTTPS_PROXY = "https_proxy"
RUNNER_VERIFY_SSL_CERT = "verify_ssl_cert"
RUNNER_USERNAME = "username"
RUNNER_PASSWORD = "password"
RUNNER_URL_HOSTS_BLACKLIST = "url_hosts_blacklist"
RUNNER_URL_HOSTS_WHITELIST = "url_hosts_whitelist"

# Lookup constants for action params
ACTION_AUTH = "auth"
ACTION_BODY = "body"
ACTION_TIMEOUT = "timeout"
ACTION_METHOD = "method"
ACTION_QUERY_PARAMS = "params"
FILE_NAME = "file_name"
FILE_CONTENT = "file_content"
FILE_CONTENT_TYPE = "file_content_type"

RESPONSE_BODY_PARSE_FUNCTIONS = {"application/json": json_decode}


class HttpRunner(ActionRunner):
    def __init__(self, runner_id):
        super(HttpRunner, self).__init__(runner_id=runner_id)
        self._on_behalf_user = cfg.CONF.system_user.user
        self._timeout = 60

    def pre_run(self):
        super(HttpRunner, self).pre_run()

        LOG.debug(
            'Entering HttpRunner.pre_run() for liveaction_id="%s"', self.liveaction_id
        )
        self._on_behalf_user = self.runner_parameters.get(
            RUNNER_ON_BEHALF_USER, self._on_behalf_user
        )
        self._url = self.runner_parameters.get(RUNNER_URL, None)
        self._headers = self.runner_parameters.get(RUNNER_HEADERS, {})

        self._cookies = self.runner_parameters.get(RUNNER_COOKIES, None)
        self._allow_redirects = self.runner_parameters.get(
            RUNNER_ALLOW_REDIRECTS, False
        )
        self._username = self.runner_parameters.get(RUNNER_USERNAME, None)
        self._password = self.runner_parameters.get(RUNNER_PASSWORD, None)
        self._http_proxy = self.runner_parameters.get(RUNNER_HTTP_PROXY, None)
        self._https_proxy = self.runner_parameters.get(RUNNER_HTTPS_PROXY, None)
        self._verify_ssl_cert = self.runner_parameters.get(RUNNER_VERIFY_SSL_CERT, None)
        self._url_hosts_blacklist = self.runner_parameters.get(
            RUNNER_URL_HOSTS_BLACKLIST, []
        )
        self._url_hosts_whitelist = self.runner_parameters.get(
            RUNNER_URL_HOSTS_WHITELIST, []
        )

    def run(self, action_parameters):
        client = self._get_http_client(action_parameters)

        if self._url_hosts_blacklist and self._url_hosts_whitelist:
            msg = (
                '"url_hosts_blacklist" and "url_hosts_whitelist" parameters are mutually '
                "exclusive. Only one should be provided."
            )
            raise ValueError(msg)

        try:
            result = client.run()
        except requests.exceptions.Timeout as e:
            result = {"error": six.text_type(e)}
            status = LIVEACTION_STATUS_TIMED_OUT
        else:
            status = HttpRunner._get_result_status(result.get("status_code", None))

        return (status, result, None)

    def _get_http_client(self, action_parameters):
        body = action_parameters.get(ACTION_BODY, None)
        timeout = float(action_parameters.get(ACTION_TIMEOUT, self._timeout))
        method = action_parameters.get(ACTION_METHOD, None)
        params = action_parameters.get(ACTION_QUERY_PARAMS, None)
        auth = action_parameters.get(ACTION_AUTH, {})

        file_name = action_parameters.get(FILE_NAME, None)
        file_content = action_parameters.get(FILE_CONTENT, None)
        file_content_type = action_parameters.get(FILE_CONTENT_TYPE, None)

        # Include our user agent and action name so requests can be tracked back
        headers = copy.deepcopy(self._headers) if self._headers else {}
        headers["User-Agent"] = "st2/v%s" % (st2_version)
        headers["X-Stanley-Action"] = self.action_name

        if file_name and file_content:
            files = {}

            if file_content_type:
                value = (file_content, file_content_type)
            else:
                value = file_content

            files[file_name] = value
        else:
            files = None

        proxies = {}

        if self._http_proxy:
            proxies["http"] = self._http_proxy

        if self._https_proxy:
            proxies["https"] = self._https_proxy

        return HTTPClient(
            url=self._url,
            method=method,
            body=body,
            params=params,
            headers=headers,
            cookies=self._cookies,
            auth=auth,
            timeout=timeout,
            allow_redirects=self._allow_redirects,
            proxies=proxies,
            files=files,
            verify=self._verify_ssl_cert,
            username=self._username,
            password=self._password,
            url_hosts_blacklist=self._url_hosts_blacklist,
            url_hosts_whitelist=self._url_hosts_whitelist,
        )

    @staticmethod
    def _get_result_status(status_code):
        return (
            LIVEACTION_STATUS_SUCCEEDED
            if status_code in SUCCESS_STATUS_CODES
            else LIVEACTION_STATUS_FAILED
        )


class HTTPClient(object):
    def __init__(
        self,
        url=None,
        method=None,
        body="",
        params=None,
        headers=None,
        cookies=None,
        auth=None,
        timeout=60,
        allow_redirects=False,
        proxies=None,
        files=None,
        verify=False,
        username=None,
        password=None,
        url_hosts_blacklist=None,
        url_hosts_whitelist=None,
    ):
        if url is None:
            raise Exception("URL must be specified.")

        if method is None:
            if files or body:
                method = "POST"
            else:
                method = "GET"

        headers = headers or {}
        normalized_headers = self._normalize_headers(headers=headers)
        if body and "content-length" not in normalized_headers:
            headers["Content-Length"] = str(len(body))

        self.url = url
        self.method = method
        self.headers = headers
        self.body = body
        self.params = params
        self.headers = headers
        self.cookies = cookies
        self.auth = auth
        self.timeout = timeout
        self.allow_redirects = allow_redirects
        self.proxies = proxies
        self.files = files
        self.verify = verify
        self.username = username
        self.password = password
        self.url_hosts_blacklist = url_hosts_blacklist or []
        self.url_hosts_whitelist = url_hosts_whitelist or []

        if self.url_hosts_blacklist and self.url_hosts_whitelist:
            msg = (
                '"url_hosts_blacklist" and "url_hosts_whitelist" parameters are mutually '
                "exclusive. Only one should be provided."
            )
            raise ValueError(msg)

    def run(self):
        results = {}
        resp = None
        json_content = self._is_json_content()

        # Check if the provided URL is blacklisted
        is_url_blacklisted = self._is_url_blacklisted(url=self.url)

        if is_url_blacklisted:
            raise ValueError('URL "%s" is blacklisted' % (self.url))

        is_url_whitelisted = self._is_url_whitelisted(url=self.url)

        if not is_url_whitelisted:
            raise ValueError('URL "%s" is not whitelisted' % (self.url))

        try:
            if json_content:
                # cast params (body) to dict
                data = self._cast_object(self.body)

                try:
                    data = json_encode(data)
                except ValueError:
                    msg = "Request body (%s) can't be parsed as JSON" % (data)
                    raise ValueError(msg)
            else:
                data = self.body

            if self.username or self.password:
                self.auth = HTTPBasicAuth(self.username, self.password)

            # Ensure data is bytes since that what request expects
            if isinstance(data, six.text_type):
                data = data.encode("utf-8")

            resp = requests.request(
                self.method,
                self.url,
                params=self.params,
                data=data,
                headers=self.headers,
                cookies=self.cookies,
                auth=self.auth,
                timeout=self.timeout,
                allow_redirects=self.allow_redirects,
                proxies=self.proxies,
                files=self.files,
                verify=self.verify,
            )

            headers = dict(resp.headers)
            body, parsed = self._parse_response_body(headers=headers, body=resp.text)

            results["status_code"] = resp.status_code
            results["body"] = body
            results["parsed"] = parsed  # flag which indicates if body has been parsed
            results["headers"] = headers
            return results
        except Exception as e:
            LOG.exception("Exception making request to remote URL: %s, %s", self.url, e)
            raise
        finally:
            if resp:
                resp.close()

    def _parse_response_body(self, headers, body):
        """
        :param body: Response body.
        :type body: ``str``

        :return: (parsed body, flag which indicates if body has been parsed)
        :rtype: (``object``, ``bool``)
        """
        body = body or ""
        headers = self._normalize_headers(headers=headers)
        content_type = headers.get("content-type", None)
        parsed = False

        if not content_type:
            return (body, parsed)

        # The header can also contain charset which we simply discard
        content_type = content_type.split(";")[0]
        parse_func = RESPONSE_BODY_PARSE_FUNCTIONS.get(content_type, None)

        if not parse_func:
            return (body, parsed)

        LOG.debug("Parsing body with content type: %s", content_type)

        try:
            body = parse_func(body)
        except Exception:
            LOG.exception("Failed to parse body")
        else:
            parsed = True

        return (body, parsed)

    def _normalize_headers(self, headers):
        """
        Normalize the header keys by lowercasing all the keys.
        """
        result = {}
        for key, value in headers.items():
            result[key.lower()] = value

        return result

    def _is_json_content(self):
        normalized = self._normalize_headers(self.headers)
        return normalized.get("content-type", None) == "application/json"

    def _cast_object(self, value):
        if isinstance(value, str) or isinstance(value, six.text_type):
            try:
                return json_decode(value)
            except:
                return ast.literal_eval(value)
        else:
            return value

    def _is_url_blacklisted(self, url):
        """
        Verify if the provided URL is blacklisted via url_hosts_blacklist runner parameter.
        """
        if not self.url_hosts_blacklist:
            # Blacklist is empty
            return False

        host = self._get_host_from_url(url=url)

        if host in self.url_hosts_blacklist:
            return True

        return False

    def _is_url_whitelisted(self, url):
        """
        Verify if the provided URL is whitelisted via url_hosts_whitelist runner parameter.
        """
        if not self.url_hosts_whitelist:
            return True

        host = self._get_host_from_url(url=url)

        if host in self.url_hosts_whitelist:
            return True

        return False

    def _get_host_from_url(self, url):
        """
        Return sanitized host (netloc) value from the provided url.
        """
        parsed = urlparse.urlparse(url)

        # Remove port and []
        host = parsed.netloc.replace("[", "").replace("]", "")

        if parsed.port is not None:
            host = host.replace(":%s" % (parsed.port), "")

        return host


def get_runner():
    return HttpRunner(str(uuid.uuid4()))


def get_metadata():
    return get_runner_metadata("http_runner")[0]
