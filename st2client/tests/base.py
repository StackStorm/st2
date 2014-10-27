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
