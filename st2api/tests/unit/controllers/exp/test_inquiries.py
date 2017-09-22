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

import copy
import json
import mock

from oslo_config import cfg

from st2common import log as logging
from six.moves import http_client
from st2common.transport.publishers import PoolPublisher
import st2common.validators.api.action as action_validator
from tests.base import BaseInquiryControllerTestCase


LOG = logging.getLogger(__name__)


ACTION_1 = {
    'name': 'st2.dummy.action1',
    'description': 'test description',
    'enabled': True,
    'pack': 'testpack',
    'runner_type': 'run-local',
}

LIVE_ACTION_1 = {
    'action': 'testpack.st2.dummy.action1',
    'parameters': {
        'cmd': 'uname -a'
    }
}

INQUIRY_ACTION = {
    'name': 'st2.dummy.ask',
    'description': 'test description',
    'enabled': True,
    'pack': 'testpack',
    'runner_type': 'inquirer',
}

INQUIRY_1 = {
    'action': 'testpack.st2.dummy.ask',
    'status': 'pending',
    'parameters': {},
    'context': {
        'parent': {
            'user': 'testu',
            'execution_id': '59b845e132ed350d396a798f',
            'pack': 'examples'
        },
        'trace_context': {'trace_tag': 'balleilaka'}
    }
}

INQUIRY_2 = {
    'action': 'testpack.st2.dummy.ask',
    'status': 'pending',
    'parameters': {
        'tag': 'superlative',
        'users': ['foo', 'bar']
    }
}

SCHEMA_DEFAULT = {
    "title": "response_data",
    "type": "object",
    "properties": {
        "continue": {
            "type": "boolean",
            "description": "Would you like to continue the workflow?"
        }
    },
    # TODO(mierdin): Fix
    "required": ["continue"]
}

SCHEMA_MULTIPLE = {
    "title": "response_data",
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "description": "What is your name?"
        },
        "pin": {
            "type": "integer",
            "description": "What is your PIN?"
        },
        "paradox": {
            "type": "boolean",
            "description": "This statement is False."
        }
    },
    # TODO(mierdin): Fix
    "required": ["name", "pin", "paradox"]
}

# This is what the result will look like if all parameters are left to their defaults
# since each parameter's used value (meaning, when runtime parameters are taken into
# account) are passed through to result
RESULT_DEFAULT = {
    "schema": SCHEMA_DEFAULT,
    "roles": [],
    "users": [],
    "tag": "",
    "ttl": 1440
}

RESULT_2 = {
    "schema": SCHEMA_DEFAULT,
    "roles": [],
    "users": ["foo", "bar"],
    "tag": "superlative",
    "ttl": 1440
}

RESULT_MULTIPLE = {
    "schema": SCHEMA_MULTIPLE,
    "roles": [],
    "users": [],
    "tag": "",
    "ttl": 1440
}

RESPONSE_MULTIPLE = {
    "name": "matt",
    "pin": 1234,
    "paradox": True
}


@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
class InquiryControllerTestCase(BaseInquiryControllerTestCase):

    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    def setUp(cls):
        super(BaseInquiryControllerTestCase, cls).setUpClass()
        cls.inquiry1 = copy.deepcopy(INQUIRY_ACTION)
        post_resp = cls.app.post_json('/v1/actions', cls.inquiry1)
        cls.inquiry1['id'] = post_resp.json['id']
        cls.action1 = copy.deepcopy(ACTION_1)
        post_resp = cls.app.post_json('/v1/actions', cls.action1)
        cls.action1['id'] = post_resp.json['id']

    def tearDown(cls):
        cls.app.delete('/v1/actions/%s' % cls.inquiry1['id'])
        cls.app.delete('/v1/actions/%s' % cls.action1['id'])
        super(BaseInquiryControllerTestCase, cls).tearDownClass()

    def test_get_all(self):
        """Test retrieval of a list of Inquiries
        """
        inquiry_count = 5
        for i in range(inquiry_count):
            self._do_create_inquiry(INQUIRY_1, RESULT_DEFAULT)
        get_all_resp = self._do_get_all()
        inquiries = get_all_resp.json
        self.assertEqual(get_all_resp.headers['X-Total-Count'], str(len(inquiries)))
        self.assertTrue(isinstance(inquiries, list))
        self.assertEqual(len(inquiries), inquiry_count)

    def test_get_all_empty(self):
        """Test retrieval of a list of Inquiries when there are none
        """
        inquiry_count = 0
        get_all_resp = self._do_get_all()
        inquiries = get_all_resp.json
        self.assertTrue(isinstance(inquiries, list))
        self.assertEqual(len(inquiries), inquiry_count)

    def test_get_all_decrease_after_respond(self):
        """Test that the inquiry list decreases when we respond to one of them
        """

        # Create inquiries
        inquiry_count = 5
        for i in range(inquiry_count):
            self._do_create_inquiry(INQUIRY_2, RESULT_DEFAULT)
        get_all_resp = self._do_get_all()
        inquiries = get_all_resp.json
        self.assertTrue(isinstance(inquiries, list))
        self.assertEqual(len(inquiries), inquiry_count)

        # Respond to one of them
        response = {"continue": True}
        self._do_respond(inquiries[0].get('id'), response)

        # Ensure the list is one smaller
        get_all_resp = self._do_get_all()
        inquiries = get_all_resp.json
        self.assertTrue(isinstance(inquiries, list))
        self.assertEqual(len(inquiries), inquiry_count - 1)

    def test_get_all_limit(self):
        """Test that the limit parameter works correctly
        """

        # Create inquiries
        inquiry_count = 5
        limit = 4
        for i in range(inquiry_count):
            self._do_create_inquiry(INQUIRY_1, RESULT_DEFAULT)
        get_all_resp = self._do_get_all(limit=limit)
        inquiries = get_all_resp.json
        self.assertTrue(isinstance(inquiries, list))
        self.assertEqual(inquiry_count, int(get_all_resp.headers['X-Total-Count']))
        self.assertEqual(len(inquiries), limit)

    def test_get_one(self):
        """Test retrieval of a single Inquiry
        """
        post_resp = self._do_create_inquiry(INQUIRY_1, RESULT_DEFAULT)
        inquiry_id = self._get_inquiry_id(post_resp)
        get_resp = self._do_get_one(inquiry_id)
        self.assertEqual(get_resp.status_int, 200)
        self.assertEqual(self._get_inquiry_id(get_resp), inquiry_id)

    def test_get_one_failed(self):
        """Test failed retrieval of an Inquiry
        """
        inquiry_id = 'asdfeoijasdf'
        get_resp = self._do_get_one(inquiry_id, expect_errors=True)
        self.assertEqual(get_resp.status_int, http_client.NOT_FOUND)
        self.assertIn('Unable to identify resource with id', get_resp.json['faultstring'])

    def test_get_one_not_an_inquiry(self):
        """Test that an attempt to retrieve a valid execution that isn't an Inquiry fails
        """
        test_exec = json.loads(self.app.post_json('/v1/executions', LIVE_ACTION_1).body)
        get_resp = self._do_get_one(test_exec.get('id'), expect_errors=True)
        self.assertEqual(get_resp.status_int, http_client.BAD_REQUEST)
        self.assertIn('is not an Inquiry', get_resp.json['faultstring'])

    def test_get_one_nondefault_params(self):
        """Ensure an Inquiry with custom parameters contains those in result
        """
        post_resp = self._do_create_inquiry(INQUIRY_2, RESULT_2)
        inquiry_id = self._get_inquiry_id(post_resp)
        get_resp = self._do_get_one(inquiry_id)
        self.assertEqual(get_resp.status_int, 200)
        self.assertEqual(self._get_inquiry_id(get_resp), inquiry_id)

        for param in ["tag", "ttl", "users", "roles", "schema"]:
            self.assertEqual(get_resp.json.get(param), RESULT_2.get(param))

    @mock.patch('st2api.controllers.exp.inquiries.action_service')
    def test_respond(self, mock_as):
        """Test that a correct response is successful
        """

        # Set up parent
        parent_id = '2934857foo'
        mock_as.get_root_liveaction.return_value = parent_id

        post_resp = self._do_create_inquiry(INQUIRY_1, RESULT_DEFAULT)
        inquiry_id = self._get_inquiry_id(post_resp)
        response = {"continue": True}
        put_resp = self._do_respond(inquiry_id, response)
        self.assertEqual(response, put_resp.json.get("response"))

        # The inquiry no longer exists, since the status should not be "pending"
        # Get the execution and confirm this.
        inquiry_execution = self._do_get_execution(inquiry_id)
        self.assertEqual(inquiry_execution.json.get('status'), 'succeeded')

        # This Inquiry is in a workflow, so has a parent. Assert that the resume
        # was requested for this parent.
        mock_as.request_resume.assert_called_once()

    @mock.patch('st2api.controllers.exp.inquiries.action_service')
    def test_respond_multiple(self, mock_as):
        """Test that a more complicated response is successful
        """

        # Set up parent
        parent_id = '2934857foo'
        mock_as.get_root_liveaction.return_value = parent_id

        post_resp = self._do_create_inquiry(INQUIRY_1, RESULT_MULTIPLE)
        inquiry_id = self._get_inquiry_id(post_resp)
        put_resp = self._do_respond(inquiry_id, RESPONSE_MULTIPLE)
        self.assertEqual(RESPONSE_MULTIPLE, put_resp.json.get("response"))

        # The inquiry no longer exists, since the status should not be "pending"
        # Get the execution and confirm this.
        inquiry_execution = self._do_get_execution(inquiry_id)
        self.assertEqual(inquiry_execution.json.get('status'), 'succeeded')

        # This Inquiry is in a workflow, so has a parent. Assert that the resume
        # was requested for this parent.
        mock_as.request_resume.assert_called_once()

    def test_respond_fail(self):
        """Test that an incorrect response is unsuccessful
        """

        post_resp = self._do_create_inquiry(INQUIRY_2, RESULT_DEFAULT)
        inquiry_id = self._get_inquiry_id(post_resp)
        response = {"continue": 123}
        put_resp = self._do_respond(inquiry_id, response, expect_errors=True)
        self.assertEqual(put_resp.status_int, http_client.BAD_REQUEST)
        self.assertIn('Response did not pass schema validation.', put_resp.json['faultstring'])

    def test_respond_not_an_inquiry(self):
        """Test that attempts to respond to an execution ID that isn't an Inquiry fails
        """
        test_exec = json.loads(self.app.post_json('/v1/executions', LIVE_ACTION_1).body)
        response = {"continue": 123}
        put_resp = self._do_respond(test_exec.get('id'), response, expect_errors=True)
        self.assertEqual(put_resp.status_int, http_client.BAD_REQUEST)
        self.assertIn('is not an Inquiry', put_resp.json['faultstring'])

    @mock.patch('st2api.controllers.exp.inquiries.action_service')
    def test_respond_no_parent(self, mock_as):
        """Test that a resume was not requested for an Inquiry without a parent
        """

        post_resp = self._do_create_inquiry(INQUIRY_2, RESULT_DEFAULT)
        inquiry_id = self._get_inquiry_id(post_resp)
        response = {"continue": True}
        put_resp = self._do_respond(inquiry_id, response)
        self.assertEqual(response, put_resp.json.get("response"))
        mock_as.request_resume.assert_not_called()

    def test_respond_duplicate_rejected(self):
        """Test that responding to an already-responded Inquiry fails
        """

        post_resp = self._do_create_inquiry(INQUIRY_2, RESULT_DEFAULT)
        inquiry_id = self._get_inquiry_id(post_resp)
        response = {"continue": True}
        put_resp = self._do_respond(inquiry_id, response)
        self.assertEqual(response, put_resp.json.get("response"))

        # The inquiry no longer exists, since the status should not be "pending"
        # Get the execution and confirm this.
        inquiry_execution = self._do_get_execution(inquiry_id)
        self.assertEqual(inquiry_execution.json.get('status'), 'succeeded')

        # A second, equivalent response attempt should not succeed, since the Inquiry
        # has already been successfully responded to
        put_resp = self._do_respond(inquiry_id, response, expect_errors=True)
        self.assertEqual(put_resp.status_int, http_client.BAD_REQUEST)
        self.assertIn('has already been responded to', put_resp.json['faultstring'])

    def test_respond_restrict_users(self):
        """Test that Inquiries can reject responses from users not in a list
        """

        # Default user for tests is "stanley", which is not in the 'users' list
        # Should be rejected
        post_resp = self._do_create_inquiry(INQUIRY_2, RESULT_2)
        inquiry_id = self._get_inquiry_id(post_resp)
        response = {"continue": True}
        put_resp = self._do_respond(inquiry_id, response, expect_errors=True)
        self.assertEqual(put_resp.status_int, http_client.FORBIDDEN)
        self.assertIn('Insufficient permission to respond based on Inquiry parameters.',
                      put_resp.json['faultstring'])

        # Responding as a use in the list should be accepted
        old_user = cfg.CONF.system_user.user
        cfg.CONF.system_user.user = "foo"
        post_resp = self._do_create_inquiry(INQUIRY_2, RESULT_2)
        inquiry_id = self._get_inquiry_id(post_resp)
        response = {"continue": True}
        put_resp = self._do_respond(inquiry_id, response)
        self.assertEqual(response, put_resp.json.get("response"))

        # Clean up
        cfg.CONF.system_user.user = old_user
