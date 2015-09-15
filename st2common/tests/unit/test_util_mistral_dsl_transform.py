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
import six
import yaml

from st2tests import DbTestCase
from st2tests.fixturesloader import FixturesLoader
from st2common.exceptions.workflow import WorkflowDefinitionException
from st2common.models.api.action import ActionAPI, RunnerTypeAPI
from st2common.persistence.action import Action
from st2common.persistence.runner import RunnerType
from st2common.util.workflow import mistral as utils


WB_PRE_XFORM_FILE = 'wb_pre_xform.yaml'
WB_POST_XFORM_FILE = 'wb_post_xform.yaml'
WF_PRE_XFORM_FILE = 'wf_pre_xform.yaml'
WF_POST_XFORM_FILE = 'wf_post_xform.yaml'
WF_NO_REQ_PARAM_FILE = 'wf_missing_required_param.yaml'
WF_UNEXP_PARAM_FILE = 'wf_has_unexpected_param.yaml'

TEST_FIXTURES = {
    'workflows': [
        WB_PRE_XFORM_FILE,
        WB_POST_XFORM_FILE,
        WF_PRE_XFORM_FILE,
        WF_POST_XFORM_FILE,
        WF_NO_REQ_PARAM_FILE,
        WF_UNEXP_PARAM_FILE
    ],
    'actions': [
        'local.yaml',
        'a1.yaml',
        'a2.yaml',
        'action1.yaml'
    ],
    'runners': [
        'run-local.yaml',
        'testrunner1.yaml',
        'testrunner2.yaml'
    ]
}

PACK = 'generic'
LOADER = FixturesLoader()
FIXTURES = LOADER.load_fixtures(fixtures_pack=PACK, fixtures_dict=TEST_FIXTURES)
WB_PRE_XFORM_PATH = LOADER.get_fixture_file_path_abs(PACK, 'workflows', WB_PRE_XFORM_FILE)
WB_PRE_XFORM_DEF = FIXTURES['workflows'][WB_PRE_XFORM_FILE]
WB_POST_XFORM_PATH = LOADER.get_fixture_file_path_abs(PACK, 'workflows', WB_POST_XFORM_FILE)
WB_POST_XFORM_DEF = FIXTURES['workflows'][WB_POST_XFORM_FILE]
WF_PRE_XFORM_PATH = LOADER.get_fixture_file_path_abs(PACK, 'workflows', WF_PRE_XFORM_FILE)
WF_PRE_XFORM_DEF = FIXTURES['workflows'][WF_PRE_XFORM_FILE]
WF_POST_XFORM_PATH = LOADER.get_fixture_file_path_abs(PACK, 'workflows', WF_POST_XFORM_FILE)
WF_POST_XFORM_DEF = FIXTURES['workflows'][WF_POST_XFORM_FILE]
WF_NO_REQ_PARAM_PATH = LOADER.get_fixture_file_path_abs(PACK, 'workflows', WF_NO_REQ_PARAM_FILE)
WF_NO_REQ_PARAM_DEF = FIXTURES['workflows'][WF_NO_REQ_PARAM_FILE]
WF_UNEXP_PARAM_PATH = LOADER.get_fixture_file_path_abs(PACK, 'workflows', WF_UNEXP_PARAM_FILE)
WF_UNEXP_PARAM_DEF = FIXTURES['workflows'][WF_UNEXP_PARAM_FILE]


class DSLTransformTestCase(DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(DSLTransformTestCase, cls).setUpClass()

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

    def test_transform_workbook_dsl_yaml(self):
        def_yaml = self._read_file_content(WB_PRE_XFORM_PATH)
        new_def = utils.transform_definition(def_yaml)
        actual = yaml.safe_load(new_def)
        expected = copy.deepcopy(WB_POST_XFORM_DEF)
        self.assertDictEqual(actual, expected)

    def test_transform_workbook_dsl_dict(self):
        def_dict = self._read_yaml_file_as_json(WB_PRE_XFORM_PATH)
        actual = utils.transform_definition(def_dict)
        expected = copy.deepcopy(WB_POST_XFORM_DEF)
        self.assertDictEqual(actual, expected)

    def test_transform_workflow_dsl_yaml(self):
        def_yaml = self._read_file_content(WF_PRE_XFORM_PATH)
        new_def = utils.transform_definition(def_yaml)
        actual = yaml.safe_load(new_def)
        expected = copy.deepcopy(WF_POST_XFORM_DEF)
        self.assertDictEqual(actual, expected)

    def test_transform_workflow_dsl_dict(self):
        def_dict = self._read_yaml_file_as_json(WF_PRE_XFORM_PATH)
        actual = utils.transform_definition(def_dict)
        expected = copy.deepcopy(WF_POST_XFORM_DEF)
        self.assertDictEqual(actual, expected)

    def test_required_action_params_failure(self):
        def_dict = self._read_yaml_file_as_json(WF_NO_REQ_PARAM_PATH)

        with self.assertRaises(WorkflowDefinitionException) as cm:
            utils.transform_definition(def_dict)

        self.assertIn('Missing required parameters', cm.exception.message)

    def test_unexpected_action_params_failure(self):
        def_dict = self._read_yaml_file_as_json(WF_UNEXP_PARAM_PATH)

        with self.assertRaises(WorkflowDefinitionException) as cm:
            utils.transform_definition(def_dict)

        self.assertIn('Unexpected parameters', cm.exception.message)

    def test_deprecated_callback_action(self):
        def_dict = self._read_yaml_file_as_json(WB_PRE_XFORM_PATH)
        def_dict['workflows']['main']['tasks']['callback'] = {'action': 'st2.callback'}
        def_yaml = yaml.safe_dump(def_dict)
        self.assertRaises(WorkflowDefinitionException, utils.transform_definition, def_yaml)
