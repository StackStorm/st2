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
import copy
import json
import mock
import requests
import argparse
import logging
import uuid

from tests import base
from st2client import shell
from six.moves import range

LOG = logging.getLogger(__name__)


def _randomize_inquiry_id(inquiry):
    newinquiry = copy.deepcopy(inquiry)
    newinquiry['id'] = str(uuid.uuid4())
    # ID can't have '1440' in it, otherwise our `count()` fails
    # when inspecting the inquiry list output for test:
    # test_list_inquiries_limit()
    while '1440' in newinquiry['id']:
        newinquiry['id'] = str(uuid.uuid4())
    return newinquiry


def _generate_inquiries(count):
    return [_randomize_inquiry_id(INQUIRY_1) for i in range(count)]


class TestInquiryBase(base.BaseCLITestCase):
    """Base class for "inquiry" CLI tests
    """

    capture_output = True

    def __init__(self, *args, **kwargs):
        super(TestInquiryBase, self).__init__(*args, **kwargs)

        self.parser = argparse.ArgumentParser()
        self.parser.add_argument('-t', '--token', dest='token')
        self.parser.add_argument('--api-key', dest='api_key')
        self.shell = shell.Shell()

    def setUp(self):
        super(TestInquiryBase, self).setUp()

    def tearDown(self):
        super(TestInquiryBase, self).tearDown()


SCHEMA_DEFAULT = {
    "title": "response_data",
    "type": "object",
    "properties": {
        "continue": {
            "type": "boolean",
            "description": "Would you like to continue the workflow?",
            "required": True
        }
    },
}

RESPONSE_DEFAULT = {
    "continue": True
}

SCHEMA_MULTIPLE = {
    "title": "response_data",
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "description": "What is your name?",
            "required": True
        },
        "pin": {
            "type": "integer",
            "description": "What is your PIN?",
            "required": True
        },
        "paradox": {
            "type": "boolean",
            "description": "This statement is False.",
            "required": True
        }
    },
}

RESPONSE_MULTIPLE = {
    "name": "matt",
    "pin": 1234,
    "paradox": True
}

RESPONSE_BAD = {
    "foo": "bar"
}

INQUIRY_1 = {
    "id": "abcdef",
    "schema": SCHEMA_DEFAULT,
    "roles": [],
    "users": [],
    "route": "",
    "ttl": 1440
}

INQUIRY_MULTIPLE = {
    "id": "beef",
    "schema": SCHEMA_MULTIPLE,
    "roles": [],
    "users": [],
    "route": "",
    "ttl": 1440
}


class TestInquirySubcommands(TestInquiryBase):

    @mock.patch.object(
        requests, 'get',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(INQUIRY_1), 200, 'OK')))
    def test_get_inquiry(self):
        """Test retrieval of a single inquiry
        """
        inquiry_id = 'abcdef'
        args = ['inquiry', 'get', inquiry_id]
        retcode = self.shell.run(args)
        self.assertEqual(retcode, 0)

    @mock.patch.object(
        requests, 'get',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps({}), 404, 'NOT FOUND')))
    def test_get_inquiry_not_found(self):
        """Test retrieval of a inquiry that doesn't exist
        """
        inquiry_id = 'asdbv'
        args = ['inquiry', 'get', inquiry_id]
        retcode = self.shell.run(args)
        self.assertEqual('Inquiry "%s" is not found.\n\n' % inquiry_id, self.stdout.getvalue())
        self.assertEqual(retcode, 2)

    @mock.patch.object(
        requests, 'get',
        mock.MagicMock(return_value=(base.FakeResponse(
            json.dumps([INQUIRY_1]), 200, 'OK', {'X-Total-Count': '1'}
        ))))
    def test_list_inquiries(self):
        """Test retrieval of a list of Inquiries
        """
        args = ['inquiry', 'list']
        retcode = self.shell.run(args)
        self.assertEqual(retcode, 0)
        self.assertEqual(self.stdout.getvalue().count('1440'), 1)

    @mock.patch.object(
        requests, 'get',
        mock.MagicMock(return_value=(base.FakeResponse(
            json.dumps(_generate_inquiries(50)), 200, 'OK', {'X-Total-Count': '55'}
        ))))
    def test_list_inquiries_limit(self):
        """Test retrieval of a list of Inquiries while using the "limit" option
        """
        args = ['inquiry', 'list', '-n', '50']
        retcode = self.shell.run(args)
        self.assertEqual(retcode, 0)
        self.assertEqual(self.stdout.getvalue().count('1440'), 50)
        self.assertTrue('Note: Only first 50 inquiries are displayed.' in self.stderr.getvalue())

    @mock.patch.object(
        requests, 'get',
        mock.MagicMock(return_value=(base.FakeResponse(
            json.dumps([]), 200, 'OK', {'X-Total-Count': '0'}
        ))))
    def test_list_empty_inquiries(self):
        """Test empty list of Inquiries
        """
        args = ['inquiry', 'list']
        retcode = self.shell.run(args)
        self.assertEqual(retcode, 0)

    @mock.patch.object(
        requests, 'get',
        mock.MagicMock(return_value=(base.FakeResponse(
            json.dumps(INQUIRY_1), 200, 'OK'
        ))))
    @mock.patch.object(
        requests, 'put',
        mock.MagicMock(return_value=(base.FakeResponse(
            json.dumps({"id": "abcdef", "response": RESPONSE_DEFAULT}), 200, 'OK'
        ))))
    @mock.patch('st2client.commands.inquiry.InteractiveForm')
    def test_respond(self, mock_form):
        """Test interactive response
        """
        form_instance = mock_form.return_value
        form_instance.initiate_dialog.return_value = RESPONSE_DEFAULT
        args = ['inquiry', 'respond', 'abcdef']
        retcode = self.shell.run(args)
        self.assertEqual(retcode, 0)

    @mock.patch.object(
        requests, 'get',
        mock.MagicMock(return_value=(base.FakeResponse(
            json.dumps(INQUIRY_1), 200, 'OK'
        ))))
    @mock.patch.object(
        requests, 'put',
        mock.MagicMock(return_value=(base.FakeResponse(
            json.dumps({"id": "abcdef", "response": RESPONSE_DEFAULT}), 200, 'OK'
        ))))
    def test_respond_response_flag(self):
        """Test response without interactive mode
        """
        args = ['inquiry', 'respond', '-r', '"%s"' % RESPONSE_DEFAULT, 'abcdef']
        retcode = self.shell.run(args)
        self.assertEqual(retcode, 0)

    @mock.patch.object(
        requests, 'get',
        mock.MagicMock(return_value=(base.FakeResponse(
            json.dumps(INQUIRY_1), 200, 'OK'
        ))))
    @mock.patch.object(
        requests, 'put',
        mock.MagicMock(return_value=(base.FakeResponse(
            json.dumps({}), 400, '400 Client Error: Bad Request'
        ))))
    def test_respond_invalid(self):
        """Test invalid response
        """
        args = ['inquiry', 'respond', '-r', '"%s"' % RESPONSE_BAD, 'abcdef']
        retcode = self.shell.run(args)
        self.assertEqual(retcode, 1)
        self.assertEqual('ERROR: 400 Client Error: Bad Request', self.stdout.getvalue().strip())

    def test_respond_nonexistent_inquiry(self):
        """Test responding to an inquiry that doesn't exist
        """
        inquiry_id = '134234'
        args = ['inquiry', 'respond', '-r', '"%s"' % RESPONSE_DEFAULT, inquiry_id]
        retcode = self.shell.run(args)
        self.assertEqual(retcode, 1)
        self.assertEqual('ERROR: Resource with id "%s" doesn\'t exist.' % inquiry_id,
                         self.stdout.getvalue().strip())

    @mock.patch.object(
        requests, 'get',
        mock.MagicMock(return_value=(base.FakeResponse(
            json.dumps({}), 404, '404 Client Error: Not Found'
        ))))
    @mock.patch('st2client.commands.inquiry.InteractiveForm')
    def test_respond_nonexistent_inquiry_interactive(self, mock_form):
        """Test interactively responding to an inquiry that doesn't exist

        Interactive mode (omitting -r flag) retrieves the inquiry with GET before
        responding with PUT, in order to retrieve the desired schema for this inquiry.
        So, we want to test that interaction separately.
        """
        inquiry_id = '253432'
        form_instance = mock_form.return_value
        form_instance.initiate_dialog.return_value = RESPONSE_DEFAULT
        args = ['inquiry', 'respond', inquiry_id]
        retcode = self.shell.run(args)
        self.assertEqual(retcode, 1)
        self.assertEqual('ERROR: Resource with id "%s" doesn\'t exist.' % inquiry_id,
                         self.stdout.getvalue().strip())
