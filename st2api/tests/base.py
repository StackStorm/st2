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

try:
    import simplejson as json
except ImportError:
    import json

from st2api import app
from st2tests.api import BaseFunctionalTest
from st2tests.base import CleanDbTestCase
from st2tests.api import BaseAPIControllerWithRBACTestCase

__all__ = [
    'FunctionalTest',

    'APIControllerWithRBACTestCase',
    'APIControllerWithIncludeAndExcludeFilterTestCase',

    'FakeResponse',

    'BaseInquiryControllerTestCase'
]


class FunctionalTest(BaseFunctionalTest):
    app_module = app


class APIControllerWithRBACTestCase(BaseAPIControllerWithRBACTestCase):
    app_module = app


class APIControllerWithIncludeAndExcludeFilterTestCase(object):
    """
    Base class which is to be inherited from the API controller test cases which support
    ?exclude_filters and ?include_filters query param filters.
    """

    # Controller get all path (e.g. "/v1/actions", /v1/rules, etc)
    get_all_path = None

    # API controller class
    controller_cls = None

    # Name of the model field to filter on
    include_attribute_field_name = None

    # Name of the model field to filter on
    exclude_attribute_field_name = None

    def test_get_all_exclude_attributes_and_include_attributes_are_mutually_exclusive(self):
        url = self.get_all_path + '?include_attributes=id&exclude_attributes=id'
        resp = self.app.get(url, expect_errors=True)
        self.assertEqual(resp.status_int, 400)
        expected_msg = ('exclude.*? and include.*? arguments are mutually exclusive. '
                        'You need to provide either one or another, but not both.')
        self.assertRegexpMatches(resp.json['faultstring'], expected_msg)

    def test_get_all_invalid_exclude_and_include_parameter(self):
        # 1. Invalid exclude_attributes field
        url = self.get_all_path + '?exclude_attributes=invalid_field'
        resp = self.app.get(url, expect_errors=True)

        expected_msg = ('Invalid or unsupported exclude attribute specified: .*invalid_field.*')
        self.assertEqual(resp.status_int, 400)
        self.assertRegexpMatches(resp.json['faultstring'], expected_msg)

        # 2. Invalid include_attributes field
        url = self.get_all_path + '?include_attributes=invalid_field'
        resp = self.app.get(url, expect_errors=True)

        expected_msg = ('Invalid or unsupported include attribute specified: .*invalid_field.*')
        self.assertEqual(resp.status_int, 400)
        self.assertRegexpMatches(resp.json['faultstring'], expected_msg)

    def test_get_all_include_attributes_filter(self):
        mandatory_include_fields = self.controller_cls.mandatory_include_fields

        # Create any resources needed by those tests (if not already created inside setUp /
        # setUpClass)
        object_ids = self._insert_mock_models()

        # Valid include attribute  - mandatory field which should always be included
        resp = self.app.get('%s?include_attributes=%s' % (self.get_all_path,
                                                          mandatory_include_fields[0]))

        self.assertEqual(resp.status_int, 200)
        self.assertTrue(len(resp.json) >= 1)
        self.assertEqual(len(resp.json), len(object_ids))
        self.assertEqual(len(resp.json[0].keys()), len(mandatory_include_fields))

        # Verify all mandatory fields are include
        for field in mandatory_include_fields:
            self.assertTrue(field in resp.json[0])

        # Valid include attribute - not a mandatory field
        include_field = self.include_attribute_field_name
        assert include_field not in mandatory_include_fields

        resp = self.app.get('%s?include_attributes=%s' % (self.get_all_path, include_field))

        self.assertEqual(resp.status_int, 200)
        self.assertTrue(len(resp.json) >= 1)
        self.assertEqual(len(resp.json), len(object_ids))
        self.assertEqual(len(resp.json[0].keys()), len(mandatory_include_fields) + 1)

        for field in [include_field] + mandatory_include_fields:
            self.assertTrue(field in resp.json[0])

        # Delete mock resources
        self._delete_mock_models(object_ids)

    def test_get_all_exclude_attributes_filter(self):
        # Create any resources needed by those tests (if not already created inside setUp /
        # setUpClass)
        object_ids = self._insert_mock_models()

        # Valid exclude attribute

        # 1. Verify attribute is present when no filter is provided
        exclude_attribute = self.exclude_attribute_field_name
        resp = self.app.get(self.get_all_path)

        self.assertEqual(resp.status_int, 200)
        self.assertTrue(len(resp.json) >= 1)
        self.assertEqual(len(resp.json), len(object_ids))
        self.assertTrue(exclude_attribute in resp.json[0])

        # 2. Verify attribute is excluded when filter is provided
        exclude_attribute = self.exclude_attribute_field_name
        resp = self.app.get('%s?exclude_attributes=%s' % (self.get_all_path,
                                                          exclude_attribute))

        self.assertEqual(resp.status_int, 200)
        self.assertTrue(len(resp.json) >= 1)
        self.assertEqual(len(resp.json), len(object_ids))
        self.assertFalse(exclude_attribute in resp.json[0])

        self._delete_mock_models(object_ids)

    def _insert_mock_models(self):
        """
        Insert mock models used for get all filter tests.

        If the test class inserts mock models inside setUp / setUpClass method, this function
        should just return the ids of inserted models.
        """
        return []

    def _delete_mock_models(self, object_ids):
        """
        Delete mock models / objects used by get all filter tests.

        If the test class inserts mock models inside setUp / setUpClass method, this method should
        be overridden and made a no-op.
        """
        for object_id in object_ids:
            self._do_delete(object_id)


class FakeResponse(object):

    def __init__(self, text, status_code, reason):
        self.text = text
        self.status_code = status_code
        self.reason = reason

    def json(self):
        return json.loads(self.text)

    def raise_for_status(self):
        raise Exception(self.reason)


class BaseActionExecutionControllerTestCase(object):

    @staticmethod
    def _get_actionexecution_id(resp):
        return resp.json['id']

    @staticmethod
    def _get_liveaction_id(resp):
        return resp.json['liveaction']['id']

    def _do_get_one(self, actionexecution_id, *args, **kwargs):
        return self.app.get('/v1/executions/%s' % actionexecution_id, *args, **kwargs)

    def _do_post(self, liveaction, *args, **kwargs):
        return self.app.post_json('/v1/executions', liveaction, *args, **kwargs)

    def _do_delete(self, actionexecution_id, expect_errors=False):
        return self.app.delete('/v1/executions/%s' % actionexecution_id,
                               expect_errors=expect_errors)

    def _do_put(self, actionexecution_id, updates, *args, **kwargs):
        return self.app.put_json('/v1/executions/%s' % actionexecution_id, updates, *args, **kwargs)


class BaseInquiryControllerTestCase(BaseFunctionalTest, CleanDbTestCase):
    """Base class for non-RBAC tests for Inquiry API

    Inherits from CleanDbTestCase to preserve atomicity between tests
    """

    enable_auth = False
    app_module = app

    @staticmethod
    def _get_inquiry_id(resp):
        return resp.json['id']

    def _do_get_execution(self, actionexecution_id, *args, **kwargs):
        return self.app.get('/v1/executions/%s' % actionexecution_id, *args, **kwargs)

    def _do_get_one(self, inquiry_id, *args, **kwargs):
        return self.app.get('/exp/inquiries/%s' % inquiry_id, *args, **kwargs)

    def _do_get_all(self, limit=50, *args, **kwargs):
        return self.app.get('/exp/inquiries/?limit=%s' % limit, *args, **kwargs)

    def _do_respond(self, inquiry_id, response, *args, **kwargs):
        payload = {
            "id": inquiry_id,
            "response": response
        }
        return self.app.put_json('/exp/inquiries/%s' % inquiry_id, payload, *args, **kwargs)

    def _do_create_inquiry(self, liveaction, result, status='pending', *args, **kwargs):
        post_resp = self.app.post_json('/v1/executions', liveaction, *args, **kwargs)
        inquiry_id = self._get_inquiry_id(post_resp)
        updates = {'status': status, 'result': result}
        return self.app.put_json('/v1/executions/%s' % inquiry_id, updates, *args, **kwargs)
