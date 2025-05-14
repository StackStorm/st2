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
import os
import sys
import json
import logging

import six
import unittest

from st2client import models


LOG = logging.getLogger(__name__)

FAKE_ENDPOINT = "http://127.0.0.1:8268"

RESOURCES = [
    {
        "id": "123",
        "name": "abc",
    },
    {"id": "456", "name": "def"},
]


class FakeResource(models.Resource):
    _plural = "FakeResources"


class FakeResponse(object):
    def __init__(self, text, status_code, reason, *args):
        self.text = text
        self.content = text
        self.status_code = status_code
        self.reason = reason
        if args:
            self.headers = args[0]

    def json(self):
        return json.loads(self.text)

    def raise_for_status(self):
        raise Exception(self.reason)


class FakeClient(object):
    def __init__(self):
        self.managers = {
            "FakeResource": models.ResourceManager(FakeResource, FAKE_ENDPOINT)
        }


class FakeApp(object):
    def __init__(self):
        self.client = FakeClient()


class BaseCLITestCase(unittest.TestCase):
    capture_output = (
        True  # if True, stdout and stderr are saved to self.stdout and self.stderr
    )

    stdout = six.moves.StringIO()
    stderr = six.moves.StringIO()

    DEFAULT_SKIP_CONFIG = "1"

    def setUp(self):
        super(BaseCLITestCase, self).setUp()

        # Setup environment
        for var in [
            "ST2_BASE_URL",
            "ST2_AUTH_URL",
            "ST2_API_URL",
            "ST2_STREAM_URL",
            "ST2_AUTH_TOKEN",
            "ST2_CONFIG_FILE",
            "ST2_API_KEY",
        ]:
            if var in os.environ:
                del os.environ[var]

        os.environ["ST2_CLI_SKIP_CONFIG"] = self.DEFAULT_SKIP_CONFIG

        if self.capture_output:
            # Make sure we reset it for each test class instance
            self.stdout = six.moves.StringIO()
            self.stderr = six.moves.StringIO()

            sys.stdout = self.stdout
            sys.stderr = self.stderr

    def tearDown(self):
        super(BaseCLITestCase, self).tearDown()

        if self.capture_output:
            # Reset to original stdout and stderr.
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__

        # On failure, we also print values of accumulated stdout and stderr
        # to make troubleshooting easier
        # TODO: nosetests specific make sure to update when / if switching to pytest
        errors = getattr(self.__dict__.get("_outcome", None), "errors", [])

        if len(errors) >= 1:
            stdout = self.stdout.getvalue()
            stderr = self.stderr.getvalue()

            print("")
            print("Captured stdout: %s" % (stdout))
            print("Captured stderr: %s" % (stderr))
            print("")

    def _reset_output_streams(self):
        """
        Reset / clear stdout and stderr stream.
        """

        self.stdout.seek(0)
        self.stdout.truncate()
        self.stderr.seek(0)
        self.stderr.truncate()

        # Verify it has been reset correctly
        self.assertEqual(self.stdout.getvalue(), "")
        self.assertEqual(self.stderr.getvalue(), "")
