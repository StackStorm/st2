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

from mistralclient.api.v2 import workbooks
from mistralclient.api.v2 import workflows
import mock
import six
import yaml

from st2common.models.api.action import ActionAPI, RunnerTypeAPI
from st2common.persistence.action import Action
from st2common.persistence.runner import RunnerType
from st2tests.fixturesloader import FixturesLoader
from st2tests.api import FunctionalTest


WB_PRE_XFORM_FILE = 'wb_pre_xform.yaml'
WB_POST_XFORM_FILE = 'wb_post_xform.yaml'
WB_INVALID_SYNTAX_FILE = 'wb_invalid_syntax.yaml'
WB_INVALID_YAQL_FILE = 'wb_invalid_yaql.yaml'
WF_PRE_XFORM_FILE = 'wf_pre_xform.yaml'
WF_POST_XFORM_FILE = 'wf_post_xform.yaml'
WF_NO_REQ_PARAM_FILE = 'wf_missing_required_param.yaml'
WF_UNEXP_PARAM_FILE = 'wf_has_unexpected_param.yaml'
WF_INVALID_SYNTAX_FILE = 'wf_invalid_syntax.yaml'
WF_INVALID_YAQL_FILE = 'wf_invalid_yaql.yaml'

TEST_FIXTURES = {
    'workflows': [
        WB_PRE_XFORM_FILE,
        WB_POST_XFORM_FILE,
        WB_INVALID_SYNTAX_FILE,
        WB_INVALID_YAQL_FILE,
        WF_PRE_XFORM_FILE,
        WF_POST_XFORM_FILE,
        WF_NO_REQ_PARAM_FILE,
        WF_UNEXP_PARAM_FILE,
        WF_INVALID_SYNTAX_FILE,
        WF_INVALID_YAQL_FILE
    ],
    'actions': [
        'a1.yaml',
        'a2.yaml',
        'action1.yaml'
    ],
    'runners': [
        'testrunner1.yaml',
        'testrunner2.yaml'
    ]
}

PACK = 'generic'
LOADER = FixturesLoader()
FIXTURES = LOADER.load_fixtures(fixtures_pack=PACK, fixtures_dict=TEST_FIXTURES)
WB_PRE_XFORM_PATH = LOADER.get_fixture_file_path_abs(PACK, 'workflows', WB_PRE_XFORM_FILE)
WB_INVALID_SYNTAX_PATH = LOADER.get_fixture_file_path_abs(PACK, 'workflows', WB_INVALID_SYNTAX_FILE)
WB_INVALID_YAQL_PATH = LOADER.get_fixture_file_path_abs(PACK, 'workflows', WB_INVALID_YAQL_FILE)
WF_PRE_XFORM_PATH = LOADER.get_fixture_file_path_abs(PACK, 'workflows', WF_PRE_XFORM_FILE)
WF_NO_REQ_PARAM_PATH = LOADER.get_fixture_file_path_abs(PACK, 'workflows', WF_NO_REQ_PARAM_FILE)
WF_UNEXP_PARAM_PATH = LOADER.get_fixture_file_path_abs(PACK, 'workflows', WF_UNEXP_PARAM_FILE)
WF_INVALID_SYNTAX_PATH = LOADER.get_fixture_file_path_abs(PACK, 'workflows', WF_INVALID_SYNTAX_FILE)
WF_INVALID_YAQL_PATH = LOADER.get_fixture_file_path_abs(PACK, 'workflows', WF_INVALID_YAQL_FILE)


class MistralValidationControllerTest(FunctionalTest):

    @classmethod
    def setUpClass(cls):
        super(MistralValidationControllerTest, cls).setUpClass()

        for _, fixture in six.iteritems(FIXTURES['runners']):
            instance = RunnerTypeAPI(**fixture)
            RunnerType.add_or_update(RunnerTypeAPI.to_model(instance))

        for _, fixture in six.iteritems(FIXTURES['actions']):
            instance = ActionAPI(**fixture)
            Action.add_or_update(ActionAPI.to_model(instance))

    def _read_file_content(self, path):
        with open(path, 'r') as f:
            return f.read()

    def _read_yaml_file_as_json(self, path):
        def_yaml = self._read_file_content(path)
        return yaml.safe_load(def_yaml)

    def __do_post(self, definition, expect_errors=False):
        return self.app.post('/exp/validation/mistral', definition, expect_errors=expect_errors,
                             content_type='text/plain')

    @mock.patch.object(
        workbooks.WorkbookManager, 'validate',
        mock.MagicMock(
            return_value={
                'valid': False,
                'error': 'Invalid DSL: \'version\' is a required property\n'}))
    def test_missing_version(self):
        def_dict = self._read_yaml_file_as_json(WB_PRE_XFORM_PATH)
        del def_dict['version']
        def_yaml = yaml.safe_dump(def_dict)
        resp = self.__do_post(def_yaml)

        expected = [
            {
                'type': 'schema',
                'path': '',
                'message': '\'version\' is a required property'
            }
        ]

        self.assertEqual(200, resp.status_int)
        self.assertListEqual(expected, resp.json)

    @mock.patch.object(
        workbooks.WorkbookManager, 'validate',
        mock.MagicMock(
            return_value={
                'valid': False,
                'error': 'Invalid DSL: Unsupported DSL version\n'}))
    def test_unsupported_version(self):
        def_dict = self._read_yaml_file_as_json(WB_PRE_XFORM_PATH)
        def_dict['version'] = '1.0'
        def_yaml = yaml.safe_dump(def_dict)
        resp = self.__do_post(def_yaml)

        expected = [
            {
                'type': 'schema',
                'path': '',
                'message': 'Unsupported DSL version'
            }
        ]

        self.assertEqual(200, resp.status_int)
        self.assertListEqual(expected, resp.json)

    @mock.patch.object(
        workflows.WorkflowManager, 'validate',
        mock.MagicMock(return_value={'valid': True}))
    def test_required_action_params_failure(self):
        def_yaml = self._read_file_content(WF_NO_REQ_PARAM_PATH)
        resp = self.__do_post(def_yaml)

        expected = [
            {
                'type': 'action',
                'path': '',
                'message': 'Missing required parameters in "task1" '
                           'for action "wolfpack.action-1": "actionstr"'
            }
        ]

        self.assertEqual(200, resp.status_int)
        self.assertListEqual(expected, resp.json)

    @mock.patch.object(
        workflows.WorkflowManager, 'validate',
        mock.MagicMock(return_value={'valid': True}))
    def test_unexpected_action_params_failure(self):
        def_yaml = self._read_file_content(WF_UNEXP_PARAM_PATH)
        resp = self.__do_post(def_yaml)

        expected = [
            {
                'type': 'action',
                'path': '',
                'message': 'Unexpected parameters in "task1" '
                           'for action "wolfpack.action-1": "foo"'
            }
        ]

        self.assertEqual(200, resp.status_int)
        self.assertListEqual(expected, resp.json)

    @mock.patch.object(
        workbooks.WorkbookManager, 'validate',
        mock.MagicMock(return_value={'valid': True}))
    def test_deprecated_callback_action(self):
        def_dict = self._read_yaml_file_as_json(WB_PRE_XFORM_PATH)
        def_dict['workflows']['main']['tasks']['callback'] = {'action': 'st2.callback'}
        def_yaml = yaml.safe_dump(def_dict)
        resp = self.__do_post(def_yaml)

        expected = [
            {
                'type': 'action',
                'path': '',
                'message': 'st2.callback is deprecated.'
            }
        ]

        self.assertEqual(200, resp.status_int)
        self.assertListEqual(expected, resp.json)

    @mock.patch.object(
        workbooks.WorkbookManager, 'validate',
        mock.MagicMock(return_value={'valid': True}))
    def test_workbook_valid(self):
        def_yaml = self._read_file_content(WB_PRE_XFORM_PATH)
        resp = self.__do_post(def_yaml)
        self.assertEqual(200, resp.status_int)
        self.assertListEqual([], resp.json)

    @mock.patch.object(
        workbooks.WorkbookManager, 'validate',
        mock.MagicMock(
            return_value={
                'valid': False,
                'error': "Invalid DSL: foobar\n\nEpic fail\nOn instance['tasks']['task1']:\n"}))
    def test_workbook_invalid_syntax(self):
        def_yaml = self._read_file_content(WB_INVALID_SYNTAX_PATH)
        resp = self.__do_post(def_yaml)

        expected = [
            {
                'type': 'schema',
                'path': 'tasks.task1',
                'message': 'foobar'
            }
        ]

        self.assertEqual(200, resp.status_int)
        self.assertListEqual(expected, resp.json)

    @mock.patch.object(
        workbooks.WorkbookManager, 'validate',
        mock.MagicMock(
            return_value={
                'valid': False,
                'error': 'Parse error: unexpected end of statement.'}))
    def test_workbook_invalid_yaql(self):
        def_yaml = self._read_file_content(WB_INVALID_YAQL_PATH)
        resp = self.__do_post(def_yaml)

        expected = [
            {
                'type': 'yaql',
                'path': '',
                'message': 'unexpected end of statement.'
            }
        ]

        self.assertEqual(200, resp.status_int)
        self.assertListEqual(expected, resp.json)

    @mock.patch.object(
        workflows.WorkflowManager, 'validate',
        mock.MagicMock(return_value={'valid': True}))
    def test_workflow_valid(self):
        def_yaml = self._read_file_content(WF_PRE_XFORM_PATH)
        resp = self.__do_post(def_yaml)
        self.assertEqual(200, resp.status_int)
        self.assertListEqual([], resp.json)

    @mock.patch.object(
        workflows.WorkflowManager, 'validate',
        mock.MagicMock(
            return_value={
                'valid': False,
                'error': "Invalid DSL: foobar\n\nEpic fail\nOn instance['tasks']['task1']:\n"}))
    def test_workflow_invalid_syntax(self):
        def_yaml = self._read_file_content(WF_INVALID_SYNTAX_PATH)
        resp = self.__do_post(def_yaml)

        expected = [
            {
                'type': 'schema',
                'path': 'tasks.task1',
                'message': 'foobar'
            }
        ]

        self.assertEqual(200, resp.status_int)
        self.assertListEqual(expected, resp.json)

    @mock.patch.object(
        workflows.WorkflowManager, 'validate',
        mock.MagicMock(
            return_value={
                'valid': False,
                'error': 'Parse error: unexpected end of statement.'}))
    def test_workflow_invalid_yaql(self):
        def_yaml = self._read_file_content(WF_INVALID_YAQL_PATH)
        resp = self.__do_post(def_yaml)

        expected = [
            {
                'type': 'yaql',
                'path': '',
                'message': 'unexpected end of statement.'
            }
        ]

        self.assertEqual(200, resp.status_int)
        self.assertListEqual(expected, resp.json)
