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

"""
Various base classes and test utility functions for API related tests.
"""

from __future__ import absolute_import

import json

import six
import webtest
import webob.compat
import webob.request
import mock

from six.moves import urllib

from oslo_config import cfg

from st2common.router import Router
from st2common.bootstrap import runnersregistrar as runners_registrar
from st2tests.base import DbTestCase
from st2tests.base import CleanDbTestCase
from st2tests import config as tests_config

__all__ = [
    "BaseFunctionalTest",
    "FunctionalTest",
    "APIControllerWithIncludeAndExcludeFilterTestCase",
    "BaseInquiryControllerTestCase",
    "FakeResponse",
    "TestApp",
]


SUPER_SECRET_PARAMETER = (
    "SUPER_SECRET_PARAMETER_THAT_SHOULD_NEVER_APPEAR_IN_RESPONSES_OR_LOGS"
)
ANOTHER_SUPER_SECRET_PARAMETER = "ANOTHER_SUPER_SECRET_PARAMETER_TO_TEST_OVERRIDING"


class ResponseValidationError(ValueError):
    pass


class ResponseLeakError(ValueError):
    pass


# NOTE: This is not ideal, but we need to patch those functions so it works correctly for the
# tests.
# The problem is that for the unit based api tests we utilize webtest which has the same bug as
# webob when handling unicode characters in the path names and the actual unit test API code doesn't
# follow exactly the same code path as actual production code which doesn't utilize webtest
# In short, that's why important we also have end to end tests for API endpoints!
webob.request.url_unquote = urllib.parse.unquote
webob.compat.url_unquote = urllib.parse.unquote


def bytes_(s, encoding="utf-8", errors="strict"):
    if isinstance(s, six.text_type):
        return s.encode("utf-8", errors)


webob.compat.bytes_ = bytes_
webob.request.bytes_ = bytes_


class TestApp(webtest.TestApp):
    def do_request(self, req, **kwargs):
        self.cookiejar.clear()

        if req.environ["REQUEST_METHOD"] != "OPTIONS":
            # Making sure endpoint handles OPTIONS method properly
            self.options(req.environ["PATH_INFO"])

        res = super(TestApp, self).do_request(req, **kwargs)

        if res.headers.get("Warning", None):
            raise ResponseValidationError(
                "Endpoint produced invalid response. Make sure the "
                "response matches OpenAPI scheme for the endpoint."
            )

        if not kwargs.get("expect_errors", None):
            try:
                body = res.body
            except AssertionError as e:
                if "Iterator read after closed" in six.text_type(e):
                    body = b""
                else:
                    raise e

            if (
                six.b(SUPER_SECRET_PARAMETER) in body
                or six.b(ANOTHER_SUPER_SECRET_PARAMETER) in body
            ):
                raise ResponseLeakError(
                    "Endpoint response contains secret parameter. " "Find the leak."
                )

        if "Access-Control-Allow-Origin" not in res.headers:
            raise ResponseValidationError("Response missing a required CORS header")

        return res


class BaseFunctionalTest(DbTestCase):
    """
    Base test case class for testing API controllers with auth and RBAC disabled.
    """

    # App used by the tests
    app_module = None

    # By default auth is disabled
    enable_auth = False

    register_runners = True

    @classmethod
    def setUpClass(cls):
        super(BaseFunctionalTest, cls).setUpClass()
        cls._do_setUpClass()

    def tearDown(self):
        super(BaseFunctionalTest, self).tearDown()

        # Reset mock context for API requests
        if getattr(self, "request_context_mock", None):
            self.request_context_mock.stop()

            if hasattr(Router, "mock_context"):
                del Router.mock_context

    @classmethod
    def _do_setUpClass(cls):
        tests_config.parse_args()

        cfg.CONF.set_default("enable", cls.enable_auth, group="auth")

        cfg.CONF.set_override(name="enable", override=False, group="rbac")

        # TODO(manas) : register action types here for now. RunnerType registration can be moved
        # to posting to /runnertypes but that implies implementing POST.
        if cls.register_runners:
            runners_registrar.register_runners()

        cls.app = TestApp(cls.app_module.setup_app())

    def use_user(self, user_db):
        """
        Select a user which is to be used by the HTTP request following this call.
        """
        if not user_db:
            raise ValueError('"user_db" is mandatory')

        mock_context = {
            "user": user_db,
            "auth_info": {"method": "authentication token", "location": "header"},
        }
        self.request_context_mock = mock.PropertyMock(return_value=mock_context)
        Router.mock_context = self.request_context_mock


class FunctionalTest(BaseFunctionalTest):
    from st2api import app

    app_module = app


# pylint: disable=no-member
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

    # True to assert that the object count in the response matches count returned by
    # _get_model_instance method method
    test_exact_object_count = True

    # True if those tests are running with rbac enabled
    rbac_enabled = False

    def test_get_all_exclude_attributes_and_include_attributes_are_mutually_exclusive(
        self,
    ):
        if self.rbac_enabled:
            self.use_user(self.users["admin"])

        url = self.get_all_path + "?include_attributes=id&exclude_attributes=id"
        resp = self.app.get(url, expect_errors=True)
        self.assertEqual(resp.status_int, 400)
        expected_msg = (
            "exclude.*? and include.*? arguments are mutually exclusive. "
            "You need to provide either one or another, but not both."
        )
        self.assertRegexpMatches(resp.json["faultstring"], expected_msg)

    def test_get_all_invalid_exclude_and_include_parameter(self):
        if self.rbac_enabled:
            self.use_user(self.users["admin"])

        # 1. Invalid exclude_attributes field
        url = self.get_all_path + "?exclude_attributes=invalid_field"
        resp = self.app.get(url, expect_errors=True)

        expected_msg = (
            "Invalid or unsupported exclude attribute specified: .*invalid_field.*"
        )
        self.assertEqual(resp.status_int, 400)
        self.assertRegexpMatches(resp.json["faultstring"], expected_msg)

        # 2. Invalid include_attributes field
        url = self.get_all_path + "?include_attributes=invalid_field"
        resp = self.app.get(url, expect_errors=True)

        expected_msg = (
            "Invalid or unsupported include attribute specified: .*invalid_field.*"
        )
        self.assertEqual(resp.status_int, 400)
        self.assertRegexpMatches(resp.json["faultstring"], expected_msg)

    def test_get_all_include_attributes_filter(self):
        if self.rbac_enabled:
            self.use_user(self.users["admin"])

        mandatory_include_fields = self.controller_cls.mandatory_include_fields_response

        # Create any resources needed by those tests (if not already created inside setUp /
        # setUpClass)
        object_ids = self._insert_mock_models()

        # Valid include attribute  - mandatory field which should always be included
        resp = self.app.get(
            "%s?include_attributes=%s"
            % (self.get_all_path, mandatory_include_fields[0])
        )

        self.assertEqual(resp.status_int, 200)
        self.assertTrue(len(resp.json) >= 1)

        if self.test_exact_object_count:
            self.assertEqual(len(resp.json), len(object_ids))

        self.assertEqual(len(resp.json[0].keys()), len(mandatory_include_fields))

        # Verify all mandatory fields are include
        for field in mandatory_include_fields:
            self.assertResponseObjectContainsField(resp.json[0], field)

        # Valid include attribute - not a mandatory field
        include_field = self.include_attribute_field_name
        assert include_field not in mandatory_include_fields

        resp = self.app.get(
            "%s?include_attributes=%s" % (self.get_all_path, include_field)
        )

        self.assertEqual(resp.status_int, 200)
        self.assertTrue(len(resp.json) >= 1)

        if self.test_exact_object_count:
            self.assertEqual(len(resp.json), len(object_ids))

        self.assertEqual(len(resp.json[0].keys()), len(mandatory_include_fields) + 1)

        for field in [include_field] + mandatory_include_fields:
            self.assertResponseObjectContainsField(resp.json[0], field)

        # Delete mock resources
        self._delete_mock_models(object_ids)

    def test_get_all_exclude_attributes_filter(self):
        if self.rbac_enabled:
            self.use_user(self.users["admin"])

        # Create any resources needed by those tests (if not already created inside setUp /
        # setUpClass)
        object_ids = self._insert_mock_models()

        # Valid exclude attribute

        # 1. Verify attribute is present when no filter is provided
        exclude_attribute = self.exclude_attribute_field_name
        resp = self.app.get(self.get_all_path)

        self.assertEqual(resp.status_int, 200)
        self.assertTrue(len(resp.json) >= 1)

        if self.test_exact_object_count:
            self.assertEqual(len(resp.json), len(object_ids))

        self.assertIn(exclude_attribute, resp.json[0])

        # 2. Verify attribute is excluded when filter is provided
        exclude_attribute = self.exclude_attribute_field_name
        resp = self.app.get(
            "%s?exclude_attributes=%s" % (self.get_all_path, exclude_attribute)
        )

        self.assertEqual(resp.status_int, 200)
        self.assertTrue(len(resp.json) >= 1)

        if self.test_exact_object_count:
            self.assertEqual(len(resp.json), len(object_ids))

        self.assertNotIn(exclude_attribute, resp.json[0])

        self._delete_mock_models(object_ids)

    def assertResponseObjectContainsField(self, resp_item, field):
        # Handle "." and nested fields
        if "." in field:
            split = field.split(".")

            for index, field_part in enumerate(split):
                self.assertIn(field_part, resp_item)
                resp_item = resp_item[field_part]

            # Additional safety check
            self.assertEqual(index, len(split) - 1)
        else:
            self.assertIn(field, resp_item)

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

    def _do_delete(self, object_id):
        pass


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
    app = None

    @staticmethod
    def _get_actionexecution_id(resp):
        return resp.json["id"]

    @staticmethod
    def _get_liveaction_id(resp):
        return resp.json["liveaction"]["id"]

    def _do_get_one(self, actionexecution_id, *args, **kwargs):
        return self.app.get("/v1/executions/%s" % actionexecution_id, *args, **kwargs)

    def _do_post(self, liveaction, *args, **kwargs):
        return self.app.post_json("/v1/executions", liveaction, *args, **kwargs)

    def _do_delete(self, actionexecution_id, expect_errors=False):
        return self.app.delete(
            "/v1/executions/%s" % actionexecution_id, expect_errors=expect_errors
        )

    def _do_put(self, actionexecution_id, updates, *args, **kwargs):
        return self.app.put_json(
            "/v1/executions/%s" % actionexecution_id, updates, *args, **kwargs
        )


class BaseInquiryControllerTestCase(BaseFunctionalTest, CleanDbTestCase):
    """
    Base class for non-RBAC tests for Inquiry API

    Inherits from CleanDbTestCase to preserve atomicity between tests
    """

    from st2api import app

    enable_auth = False
    app_module = app

    @staticmethod
    def _get_inquiry_id(resp):
        return resp.json["id"]

    def _do_get_execution(self, actionexecution_id, *args, **kwargs):
        return self.app.get("/v1/executions/%s" % actionexecution_id, *args, **kwargs)

    def _do_get_one(self, inquiry_id, *args, **kwargs):
        return self.app.get("/v1/inquiries/%s" % inquiry_id, *args, **kwargs)

    def _do_get_all(self, limit=50, *args, **kwargs):
        return self.app.get("/v1/inquiries/?limit=%s" % limit, *args, **kwargs)

    def _do_respond(self, inquiry_id, response, *args, **kwargs):
        payload = {"id": inquiry_id, "response": response}
        return self.app.put_json(
            "/v1/inquiries/%s" % inquiry_id, payload, *args, **kwargs
        )

    def _do_create_inquiry(self, liveaction, result, status="pending", *args, **kwargs):
        post_resp = self.app.post_json("/v1/executions", liveaction, *args, **kwargs)
        inquiry_id = self._get_inquiry_id(post_resp)
        updates = {"status": status, "result": result}
        return self.app.put_json(
            "/v1/executions/%s" % inquiry_id, updates, *args, **kwargs
        )
