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

import os
import logging
import unittest2

from st2client.client import Client


LOG = logging.getLogger(__name__)


class TestClientEndpoints(unittest2.TestCase):

    def tearDown(self):
        for var in ['ST2_BASE_URL', 'ST2_API_URL', 'ST2_DATASTORE_URL']:
            if var in os.environ:
                del os.environ[var]

    def test_default(self):
        base_url = 'http://localhost'
        api_url = 'http://localhost:9101/v1'

        client = Client()
        endpoints = client.endpoints
        self.assertEqual(endpoints['base'], base_url)
        self.assertEqual(endpoints['api'], api_url)

    def test_env(self):
        base_url = 'http://www.stackstorm.com'
        api_url = 'http://www.st2.com:9101/v1'

        os.environ['ST2_BASE_URL'] = base_url
        os.environ['ST2_API_URL'] = api_url
        self.assertEqual(os.environ.get('ST2_BASE_URL'), base_url)
        self.assertEqual(os.environ.get('ST2_API_URL'), api_url)

        client = Client()
        endpoints = client.endpoints
        self.assertEqual(endpoints['base'], base_url)
        self.assertEqual(endpoints['api'], api_url)

    def test_env_base_only(self):
        base_url = 'http://www.stackstorm.com'
        api_url = 'http://www.stackstorm.com:9101/v1'

        os.environ['ST2_BASE_URL'] = base_url
        self.assertEqual(os.environ.get('ST2_BASE_URL'), base_url)
        self.assertEqual(os.environ.get('ST2_API_URL'), None)

        client = Client()
        endpoints = client.endpoints
        self.assertEqual(endpoints['base'], base_url)
        self.assertEqual(endpoints['api'], api_url)

    def test_args(self):
        base_url = 'http://www.stackstorm.com'
        api_url = 'http://www.st2.com:9101/v1'

        client = Client(base_url=base_url, api_url=api_url)
        endpoints = client.endpoints
        self.assertEqual(endpoints['base'], base_url)
        self.assertEqual(endpoints['api'], api_url)

    def test_args_base_only(self):
        base_url = 'http://www.stackstorm.com'
        api_url = 'http://www.stackstorm.com:9101/v1'

        client = Client(base_url=base_url)
        endpoints = client.endpoints
        self.assertEqual(endpoints['base'], base_url)
        self.assertEqual(endpoints['api'], api_url)
