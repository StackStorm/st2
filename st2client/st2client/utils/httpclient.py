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

import json
import requests
import logging


LOG = logging.getLogger(__name__)


def add_ssl_verify_to_kwargs(func):
    def decorate(*args, **kwargs):
        if isinstance(args[0], HTTPClient) and 'https' in getattr(args[0], 'root', ''):
            cacert = getattr(args[0], 'cacert', None)
            kwargs['verify'] = cacert if cacert else False
        return func(*args, **kwargs)
    return decorate


def add_auth_token_to_headers(func):
    def decorate(*args, **kwargs):
        token = kwargs.pop('token', None)
        if token:
            headers = kwargs.get('headers', dict())
            headers['X-Auth-Token'] = str(token)
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


class HTTPClient(object):

    def __init__(self, root, cacert=None):
        self.root = root
        self.cacert = cacert

    @add_ssl_verify_to_kwargs
    @add_auth_token_to_headers
    def get(self, url, **kwargs):
        return requests.get(self.root + url, **kwargs)

    @add_ssl_verify_to_kwargs
    @add_auth_token_to_headers
    @add_json_content_type_to_headers
    def post(self, url, data, **kwargs):
        return requests.post(self.root + url, json.dumps(data), **kwargs)

    @add_ssl_verify_to_kwargs
    @add_auth_token_to_headers
    @add_json_content_type_to_headers
    def put(self, url, data, **kwargs):
        return requests.put(self.root + url, json.dumps(data), **kwargs)

    @add_ssl_verify_to_kwargs
    @add_auth_token_to_headers
    @add_json_content_type_to_headers
    def patch(self, url, data, **kwargs):
        return requests.patch(self.root + url, data, **kwargs)

    @add_ssl_verify_to_kwargs
    @add_auth_token_to_headers
    def delete(self, url, **kwargs):
        return requests.delete(self.root + url, **kwargs)
