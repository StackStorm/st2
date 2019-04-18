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

from st2common.content import utils as content_utils
import st2common.validators.api.action as action_validator
from st2common.util.compat import mock_open_name
from st2api.controllers.v1.action_views import OverviewController

from st2tests.api import FunctionalTest
from st2tests.api import APIControllerWithIncludeAndExcludeFilterTestCase

# ACTION_1: Good action definition.
ACTION_1 = {
    'name': 'st2.dummy.action1',
    'description': 'test description',
    'enabled': True,
    'pack': 'wolfpack',
    'entry_point': 'test/action1.sh',
    'runner_type': 'local-shell-script',
    'parameters': {
        'a': {'type': 'string', 'default': 'A1'},
        'b': {'type': 'string', 'default': 'B1'}
    }
}

# ACTION_2: Good action definition. No content pack.
ACTION_2 = {
    'name': 'st2.dummy.action2',
    'description': 'test description',
    'enabled': True,
    'pack': 'wolfpack',
    'entry_point': 'test/action2.py',
    'runner_type': 'local-shell-script',
    'parameters': {
        'c': {'type': 'string', 'default': 'C1', 'position': 0},
        'd': {'type': 'string', 'default': 'D1', 'immutable': True}
    }
}


class ActionViewsOverviewControllerTestCase(FunctionalTest,
                                            APIControllerWithIncludeAndExcludeFilterTestCase):
    get_all_path = '/v1/actions/views/overview'
    controller_cls = OverviewController
    include_attribute_field_name = 'entry_point'
    exclude_attribute_field_name = 'parameters'

    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    def test_get_one(self):
        post_resp = self._do_post(ACTION_1)
        action_id = self._get_action_id(post_resp)
        try:
            get_resp = self._do_get_one(action_id)
            self.assertEqual(get_resp.status_int, 200)
            self.assertEqual(self._get_action_id(get_resp), action_id)
        finally:
            self._do_delete(action_id)

    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    def test_get_one_ref(self):
        post_resp = self._do_post(ACTION_1)
        action_id = self._get_action_id(post_resp)
        action_ref = self._get_action_ref(post_resp)
        try:
            get_resp = self._do_get_one(action_ref)
            self.assertEqual(get_resp.status_int, 200)
            self.assertEqual(get_resp.json['ref'], action_ref)
        finally:
            self._do_delete(action_id)

    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    def test_get_all_and_limit_minus_one(self):
        action_1_id = self._get_action_id(self._do_post(ACTION_1))
        action_2_id = self._get_action_id(self._do_post(ACTION_2))
        try:
            resp = self.app.get('/v1/actions/views/overview')
            self.assertEqual(resp.status_int, 200)
            self.assertEqual(len(resp.json), 2,
                             '/v1/actions/views/overview did not return all actions.')
            resp = self.app.get('/v1/actions/views/overview/?limit=-1')
            self.assertEqual(resp.status_int, 200)
            self.assertEqual(len(resp.json), 2,
                             '/v1/actions/views/overview did not return all actions.')
        finally:
            self._do_delete(action_1_id)
            self._do_delete(action_2_id)

    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    def test_get_all_negative_limit(self):
        action_1_id = self._get_action_id(self._do_post(ACTION_1))
        action_2_id = self._get_action_id(self._do_post(ACTION_2))
        try:
            resp = self.app.get('/v1/actions/views/overview/?limit=-22', expect_errors=True)
            self.assertEqual(resp.status_int, 400)
            self.assertEqual(resp.json['faultstring'],
                             u'Limit, "-22" specified, must be a positive number.')
        finally:
            self._do_delete(action_1_id)
            self._do_delete(action_2_id)

    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    def test_get_all_filter_by_name(self):
        action_1_id = self._get_action_id(self._do_post(ACTION_1))
        action_2_id = self._get_action_id(self._do_post(ACTION_2))
        try:
            resp = self.app.get('/v1/actions/views/overview?name=%s' % str('st2.dummy.action2'))
            self.assertEqual(resp.status_int, 200)
            self.assertEqual(resp.json[0]['id'], action_2_id, 'Filtering failed')
        finally:
            self._do_delete(action_1_id)
            self._do_delete(action_2_id)

    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    def test_get_all_include_attributes_filter(self):
        return super(ActionViewsOverviewControllerTestCase, self) \
            .test_get_all_include_attributes_filter()

    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    def test_get_all_exclude_attributes_filter(self):
        return super(ActionViewsOverviewControllerTestCase, self) \
            .test_get_all_include_attributes_filter()

    def _insert_mock_models(self):
        action_1_id = self._get_action_id(self._do_post(ACTION_1))
        action_2_id = self._get_action_id(self._do_post(ACTION_2))

        return [action_1_id, action_2_id]

    @staticmethod
    def _get_action_id(resp):
        return resp.json['id']

    @staticmethod
    def _get_action_ref(resp):
        return '.'.join((resp.json['pack'], resp.json['name']))

    @staticmethod
    def _get_action_name(resp):
        return resp.json['name']

    def _do_get_one(self, action_id, expect_errors=False):
        return self.app.get('/v1/actions/views/overview/%s' % action_id,
                            expect_errors=expect_errors)

    def _do_post(self, action, expect_errors=False):
        return self.app.post_json('/v1/actions', action, expect_errors=expect_errors)

    def _do_delete(self, action_id, expect_errors=False):
        return self.app.delete('/v1/actions/%s' % action_id, expect_errors=expect_errors)


class ActionViewsParametersControllerTestCase(FunctionalTest):
    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    def test_get_one(self):
        post_resp = self.app.post_json('/v1/actions', ACTION_1)
        action_id = post_resp.json['id']
        try:
            get_resp = self.app.get('/v1/actions/views/parameters/%s' % action_id)
            self.assertEqual(get_resp.status_int, 200)
        finally:
            self.app.delete('/v1/actions/%s' % action_id)


class ActionEntryPointViewControllerTestCase(FunctionalTest):
    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    @mock.patch.object(content_utils, 'get_entry_point_abs_path', mock.MagicMock(
        return_value='/path/to/file'))
    @mock.patch(mock_open_name, mock.mock_open(read_data='file content'), create=True)
    def test_get_one(self):
        post_resp = self.app.post_json('/v1/actions', ACTION_1)
        action_id = post_resp.json['id']
        try:
            get_resp = self.app.get('/v1/actions/views/entry_point/%s' % action_id)
            self.assertEqual(get_resp.status_int, 200)
        finally:
            self.app.delete('/v1/actions/%s' % action_id)

    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    @mock.patch.object(content_utils, 'get_entry_point_abs_path', mock.MagicMock(
        return_value='/path/to/file'))
    @mock.patch(mock_open_name, mock.mock_open(read_data='file content'), create=True)
    def test_get_one_ref(self):
        post_resp = self.app.post_json('/v1/actions', ACTION_1)
        action_id = post_resp.json['id']
        action_ref = '.'.join((post_resp.json['pack'], post_resp.json['name']))
        try:
            get_resp = self.app.get('/v1/actions/views/entry_point/%s' % action_ref)
            self.assertEqual(get_resp.status_int, 200)
        finally:
            self.app.delete('/v1/actions/%s' % action_id)

    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    @mock.patch.object(content_utils, 'get_entry_point_abs_path', mock.MagicMock(
        return_value='/path/to/file.yaml'))
    @mock.patch(mock_open_name, mock.mock_open(read_data='file content'), create=True)
    def test_get_one_ref_yaml_content_type(self):
        post_resp = self.app.post_json('/v1/actions', ACTION_1)
        action_id = post_resp.json['id']
        action_ref = '.'.join((post_resp.json['pack'], post_resp.json['name']))
        try:
            get_resp = self.app.get('/v1/actions/views/entry_point/%s' % action_ref)
            self.assertEqual(get_resp.status_int, 200)
            self.assertEqual(get_resp.headers['Content-Type'], 'application/x-yaml')
        finally:
            self.app.delete('/v1/actions/%s' % action_id)

    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    @mock.patch.object(content_utils, 'get_entry_point_abs_path', mock.MagicMock(
        return_value=__file__.replace('.pyc', '.py')))
    @mock.patch(mock_open_name, mock.mock_open(read_data='file content'), create=True)
    def test_get_one_ref_python_content_type(self):
        post_resp = self.app.post_json('/v1/actions', ACTION_1)
        action_id = post_resp.json['id']
        action_ref = '.'.join((post_resp.json['pack'], post_resp.json['name']))
        try:
            get_resp = self.app.get('/v1/actions/views/entry_point/%s' % action_ref)
            self.assertEqual(get_resp.status_int, 200)
            self.assertEqual(get_resp.headers['Content-Type'], 'application/x-python')
        finally:
            self.app.delete('/v1/actions/%s' % action_id)

    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    @mock.patch.object(content_utils, 'get_entry_point_abs_path', mock.MagicMock(
        return_value='/file/does/not/exist'))
    @mock.patch(mock_open_name, mock.mock_open(read_data='file content'), create=True)
    def test_get_one_ref_text_plain_content_type(self):
        post_resp = self.app.post_json('/v1/actions', ACTION_1)
        action_id = post_resp.json['id']
        action_ref = '.'.join((post_resp.json['pack'], post_resp.json['name']))
        try:
            get_resp = self.app.get('/v1/actions/views/entry_point/%s' % action_ref)
            self.assertEqual(get_resp.status_int, 200)
            self.assertEqual(get_resp.headers['Content-Type'], 'text/plain')
        finally:
            self.app.delete('/v1/actions/%s' % action_id)
