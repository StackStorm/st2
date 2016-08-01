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

from __future__ import absolute_import

import json
import logging
from pipes import quote as pquote

import requests


LOG = logging.getLogger(__name__)


def add_ssl_verify_to_kwargs(func):
    def decorate(*args, **kwargs):
        if isinstance(args[0], HTTPClient) and 'https' in getattr(args[0], 'root', ''):
            cacert = getattr(args[0], 'cacert', None)
            kwargs['verify'] = cacert if cacert is not None else False
        return func(*args, **kwargs)
    return decorate


def add_auth_token_to_headers(func):
    def decorate(*args, **kwargs):
        headers = kwargs.get('headers', dict())

        token = kwargs.pop('token', None)
        if token:
            headers['X-Auth-Token'] = str(token)
            kwargs['headers'] = headers

        api_key = kwargs.pop('api_key', None)
        if api_key:
            headers['St2-Api-Key'] = str(api_key)
            kwargs['headers'] = headers

        return func(*args, **kwargs)
    return decorate


def add_json_content_type_to_headers(func):
    def decorate(*args, **kwargs):
        headers = kwargs.get('headers', dict())
        content_type = headers.get('content-type', 'application/json')
        headers['content-type'] = content_type
        kwargs['headers'] = headers
        return func(*args, **kwargs)
    return decorate


def get_url_without_trailing_slash(value):
    """
    Function which strips a trailing slash from the provided url if one is present.

    :param value: URL to format.
    :type value: ``str``

    :rtype: ``str``
    """
    result = value[:-1] if value.endswith('/') else value
    return result


class HTTPClient(object):

    def __init__(self, root, cacert=None, debug=False):
        self.root = get_url_without_trailing_slash(root)
        self.cacert = cacert
        self.debug = debug

    @add_ssl_verify_to_kwargs
    @add_auth_token_to_headers
    def get(self, url, **kwargs):
        response = requests.get(self.root + url, **kwargs)
        response = self._response_hook(response=response)
        return response

    @add_ssl_verify_to_kwargs
    @add_auth_token_to_headers
    @add_json_content_type_to_headers
    def post(self, url, data, **kwargs):
        response = requests.post(self.root + url, json.dumps(data), **kwargs)
        response = self._response_hook(response=response)
        return response

    @add_ssl_verify_to_kwargs
    @add_auth_token_to_headers
    def post_raw(self, url, data, **kwargs):
        response = requests.post(self.root + url, data, **kwargs)
        response = self._response_hook(response=response)
        return response

    @add_ssl_verify_to_kwargs
    @add_auth_token_to_headers
    @add_json_content_type_to_headers
    def put(self, url, data, **kwargs):
        response = requests.put(self.root + url, json.dumps(data), **kwargs)
        response = self._response_hook(response=response)
        return response

    @add_ssl_verify_to_kwargs
    @add_auth_token_to_headers
    @add_json_content_type_to_headers
    def patch(self, url, data, **kwargs):
        response = requests.patch(self.root + url, data, **kwargs)
        response = self._response_hook(response=response)
        return response

    @add_ssl_verify_to_kwargs
    @add_auth_token_to_headers
    def delete(self, url, **kwargs):
        response = requests.delete(self.root + url, **kwargs)
        response = self._response_hook(response=response)
        return response

    def _response_hook(self, response):
        if self.debug:
            # Log cURL request line
            curl_line = self._get_curl_line_for_request(request=response.request)
            print("# -------- begin %d request ----------" % id(self))
            print(curl_line)
            print("# -------- begin %d response ----------" % (id(self)))
            print(response.text)
            print("# -------- end %d response ------------" % (id(self)))
            print('')

        return response

    def _get_curl_line_for_request(self, request):
        parts = ['curl']

        # method
        method = request.method.upper()
        if method in ['HEAD']:
            parts.extend(['--head'])
        else:
            parts.extend(['-X', pquote(method)])

        # headers
        for key, value in request.headers.items():
            parts.extend(['-H ', pquote('%s: %s' % (key, value))])

        # body
        if request.body:
            parts.extend(['--data-binary', pquote(request.body)])

        # URL
        parts.extend([pquote(request.url)])

        curl_line = ' '.join(parts)
        return curl_line
