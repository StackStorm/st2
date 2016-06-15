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
import sys
import json
import logging

import six
import unittest2

from st2client import models


LOG = logging.getLogger(__name__)

FAKE_ENDPOINT = 'http://127.0.0.1:8268'

RESOURCES = [
    {
        "id": "123",
        "name": "abc",
    },
    {
        "id": "456",
        "name": "def"
    }
]


class FakeResource(models.Resource):
    _plural = 'FakeResources'


class FakeResponse(object):

    def __init__(self, text, status_code, reason):
        self.text = text
        self.status_code = status_code
        self.reason = reason

    def json(self):
        return json.loads(self.text)

    def raise_for_status(self):
        raise Exception(self.reason)


class FakeClient(object):
    def __init__(self):
        self.managers = {
            'FakeResource': models.ResourceManager(FakeResource,
                                                   FAKE_ENDPOINT)
        }


class FakeApp(object):
    def __init__(self):
        self.client = FakeClient()


class BaseCLITestCase(unittest2.TestCase):
    capture_output = True  # if True, stdout and stderr are saved to self.stdout and self.stderr

    stdout = six.moves.StringIO()
    stderr = six.moves.StringIO()

    def setUp(self):
        super(BaseCLITestCase, self).setUp()

        # Setup environment
        for var in ['ST2_BASE_URL', 'ST2_AUTH_URL', 'ST2_API_URL',
                    'ST2_AUTH_TOKEN', 'ST2_CONFIG_FILE', 'ST2_API_KEY']:
            if var in os.environ:
                del os.environ[var]

        os.environ['ST2_CLI_SKIP_CONFIG'] = '1'

        if self.capture_output:
            sys.stdout = self.stdout
            sys.stderr = self.stderr

    def tearDown(self):
        super(BaseCLITestCase, self).tearDown()

        if self.capture_output:
            # Reset to original stdout and stderr.
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
