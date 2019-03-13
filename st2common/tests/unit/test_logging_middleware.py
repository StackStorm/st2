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

import mock
import unittest2

from st2common.middleware.logging import LoggingMiddleware
from st2common.constants.secrets import MASKED_ATTRIBUTE_VALUE

__all__ = [
    'LoggingMiddlewareTestCase'
]


class LoggingMiddlewareTestCase(unittest2.TestCase):
    @mock.patch('st2common.middleware.logging.LOG')
    @mock.patch('st2common.middleware.logging.Request')
    def test_secret_parameters_are_masked_in_log_message(self, mock_request, mock_log):

        def app(environ, custom_start_response):
            custom_start_response(status='200 OK', headers=[('Content-Length', 100)])
            return [None]

        router = mock.Mock()
        endpoint = mock.Mock()
        router.match.return_value = (endpoint, None)
        middleware = LoggingMiddleware(app=app, router=router)

        environ = {}
        mock_request.return_value.GET.dict_of_lists.return_value = {
            'foo': 'bar',
            'bar': 'baz',
            'x-auth-token': 'secret',
            'st2-api-key': 'secret',
            'password': 'secret',
            'st2_auth_token': 'secret',
            'token': 'secret'
        }
        middleware(environ=environ, start_response=mock.Mock())

        expected_query = {
            'foo': 'bar',
            'bar': 'baz',
            'x-auth-token': MASKED_ATTRIBUTE_VALUE,
            'st2-api-key': MASKED_ATTRIBUTE_VALUE,
            'password': MASKED_ATTRIBUTE_VALUE,
            'token': MASKED_ATTRIBUTE_VALUE,
            'st2_auth_token': MASKED_ATTRIBUTE_VALUE
        }

        call_kwargs = mock_log.info.call_args_list[0][1]
        query = call_kwargs['extra']['query']
        self.assertEqual(query, expected_query)
