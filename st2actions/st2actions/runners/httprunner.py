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

import ast
import copy
import json
import uuid

import requests
from oslo_config import cfg

from st2actions.runners import ActionRunner
from st2common import __version__ as st2_version
from st2common import log as logging
from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED
from st2common.constants.action import LIVEACTION_STATUS_FAILED
from st2common.constants.action import LIVEACTION_STATUS_TIMED_OUT

LOG = logging.getLogger(__name__)
SUCCESS_STATUS_CODES = [code for code in range(200, 207)]

# Lookup constants for runner params
RUNNER_ON_BEHALF_USER = 'user'
RUNNER_URL = 'url'
RUNNER_HEADERS = 'headers'  # Debatable whether this should be action params.
RUNNER_COOKIES = 'cookies'
RUNNER_ALLOW_REDIRECTS = 'allow_redirects'
RUNNER_HTTP_PROXY = 'http_proxy'
RUNNER_HTTPS_PROXY = 'https_proxy'
RUNNER_VERIFY_SSL_CERT = 'verify_ssl_cert'

# Lookup constants for action params
ACTION_AUTH = 'auth'
ACTION_BODY = 'body'
ACTION_TIMEOUT = 'timeout'
ACTION_METHOD = 'method'
ACTION_QUERY_PARAMS = 'params'
FILE_NAME = 'file_name'
FILE_CONTENT = 'file_content'
FILE_CONTENT_TYPE = 'file_content_type'

RESPONSE_BODY_PARSE_FUNCTIONS = {
    'application/json': json.loads
}


def get_runner():
    return HttpRunner(str(uuid.uuid4()))


class HttpRunner(ActionRunner):
    def __init__(self, runner_id):
        super(HttpRunner, self).__init__(runner_id=runner_id)
        self._on_behalf_user = cfg.CONF.system_user.user
        self._timeout = 60

    def pre_run(self):
        super(HttpRunner, self).pre_run()

        LOG.debug('Entering HttpRunner.pre_run() for liveaction_id="%s"', self.liveaction_id)
        self._on_behalf_user = self.runner_parameters.get(RUNNER_ON_BEHALF_USER,
                                                          self._on_behalf_user)
        self._url = self.runner_parameters.get(RUNNER_URL, None)
        self._headers = self.runner_parameters.get(RUNNER_HEADERS, {})

        self._cookies = self.runner_parameters.get(RUNNER_COOKIES, None)
        self._allow_redirects = self.runner_parameters.get(RUNNER_ALLOW_REDIRECTS, False)
        self._http_proxy = self.runner_parameters.get(RUNNER_HTTP_PROXY, None)
        self._https_proxy = self.runner_parameters.get(RUNNER_HTTPS_PROXY, None)
        self._verify_ssl_cert = self.runner_parameters.get(RUNNER_VERIFY_SSL_CERT, None)

    def run(self, action_parameters):
        client = self._get_http_client(action_parameters)

        try:
            result = client.run()
        except requests.exceptions.Timeout as e:
            result = {'error': str(e)}
            status = LIVEACTION_STATUS_TIMED_OUT
        else:
            status = HttpRunner._get_result_status(result.get('status_code', None))

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
        headers['User-Agent'] = 'st2/v%s' % (st2_version)
        headers['X-Stanley-Action'] = self.action_name

        if file_name and file_content:
            files = {}

            if file_content_type:
                value = (file_content, file_content_type)
            else:
                value = (file_content)

            files[file_name] = value
        else:
            files = None

        proxies = {}

        if self._http_proxy:
            proxies['http'] = self._http_proxy

        if self._https_proxy:
            proxies['https'] = self._https_proxy

        return HTTPClient(url=self._url, method=method, body=body, params=params,
                          headers=headers, cookies=self._cookies, auth=auth,
                          timeout=timeout, allow_redirects=self._allow_redirects,
                          proxies=proxies, files=files, verify=self._verify_ssl_cert)

    @staticmethod
    def _get_result_status(status_code):
        return LIVEACTION_STATUS_SUCCEEDED if status_code in SUCCESS_STATUS_CODES \
            else LIVEACTION_STATUS_FAILED


class HTTPClient(object):
    def __init__(self, url=None, method=None, body='', params=None, headers=None, cookies=None,
                 auth=None, timeout=60, allow_redirects=False, proxies=None,
                 files=None, verify=False):
        if url is None:
            raise Exception('URL must be specified.')

        if method is None:
            if files or body:
                method = 'POST'
            else:
                method = 'GET'

        headers = headers or {}
        normalized_headers = self._normalize_headers(headers=headers)
        if body and 'content-length' not in normalized_headers:
            headers['Content-Length'] = str(len(body))

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

    def run(self):
        results = {}
        resp = None
        json_content = self._is_json_content()

        try:
            if json_content:
                # cast params (body) to dict
                data = self._cast_object(self.body)

                try:
                    data = json.dumps(data)
                except ValueError:
                    msg = 'Request body (%s) can\'t be parsed as JSON' % (data)
                    raise ValueError(msg)
            else:
                data = self.body

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
                verify=self.verify
            )

            headers = dict(resp.headers)
            body, parsed = self._parse_response_body(headers=headers, body=resp.text)

            results['status_code'] = resp.status_code
            results['body'] = body
            results['parsed'] = parsed  # flag which indicates if body has been parsed
            results['headers'] = headers
            return results
        except Exception as e:
            LOG.exception('Exception making request to remote URL: %s, %s', self.url, e)
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
        body = body or ''
        headers = self._normalize_headers(headers=headers)
        content_type = headers.get('content-type', None)
        parsed = False

        if not content_type:
            return (body, parsed)

        # The header can also contain charset which we simply discard
        content_type = content_type.split(';')[0]
        parse_func = RESPONSE_BODY_PARSE_FUNCTIONS.get(content_type, None)

        if not parse_func:
            return (body, parsed)

        LOG.debug('Parsing body with content type: %s', content_type)

        try:
            body = parse_func(body)
        except Exception:
            LOG.exception('Failed to parse body')
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
        return normalized.get('content-type', None) == 'application/json'

    def _cast_object(self, value):
        if isinstance(value, str) or isinstance(value, unicode):
            try:
                return json.loads(value)
            except:
                return ast.literal_eval(value)
        else:
            return value
