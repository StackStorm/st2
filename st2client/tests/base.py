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
import unittest2

from st2client import models


LOG = logging.getLogger(__name__)

FAKE_ENDPOINT = 'http://localhost:8268'

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
    hide_output = False  # if True, stdout and stderr will be redirected to /dev/null

    def setUp(self):
        super(BaseCLITestCase, self).setUp()

        if 'ST2_AUTH_TOKEN' in os.environ:
            del os.environ['ST2_AUTH_TOKEN']

        if self.hide_output:
            # Redirect standard output and error to null. If not, then
            # some of the print output from shell commands will pollute
            # the test output.
            sys.stdout = open(os.devnull, 'w')
            sys.stderr = open(os.devnull, 'w')

    def tearDown(self):
        super(BaseCLITestCase, self).tearDown()

        if self.hide_output:
            # Reset to original stdout and stderr.
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
