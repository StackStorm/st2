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

import yaml

from st2tests import DbTestCase
from st2tests.fixturesloader import FixturesLoader
import st2actions.bootstrap.runnersregistrar as runners_registrar
from st2actions.runners.mistral import utils
from st2common.models.api.action import ActionAPI
from st2common.persistence.action import Action


WB_PRE_XFORM_FILE = 'wb_pre_xform.yaml'
WB_POST_XFORM_FILE = 'wb_post_xform.yaml'
WF_PRE_XFORM_FILE = 'wf_pre_xform.yaml'
WF_POST_XFORM_FILE = 'wf_post_xform.yaml'
TEST_FIXTURES = {
    'workflows': [
        WB_PRE_XFORM_FILE,
        WB_POST_XFORM_FILE,
        WF_PRE_XFORM_FILE,
        WF_POST_XFORM_FILE
    ],
    'actions': ['local.yaml']
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


def _read_file_content(path):
    with open(path, 'r') as f:
        return f.read()


class DSLTransformTestCase(DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(DSLTransformTestCase, cls).setUpClass()
        runners_registrar.register_runner_types()

        action_local = ActionAPI(**copy.deepcopy(FIXTURES['actions']['local.yaml']))
        Action.add_or_update(ActionAPI.to_model(action_local))

        for action_name in ['action1', 'action2', 'action3']:
            metadata = copy.deepcopy(FIXTURES['actions']['local.yaml'])
            metadata['name'] = action_name
            metadata['pack'] = 'demo'
            action = ActionAPI(**metadata)
            Action.add_or_update(ActionAPI.to_model(action))

    @staticmethod
    def _read_file_content(path):
        with open(path, 'r') as f:
            return f.read()

    def test_invalid_dsl_version(self):
        def_yaml = _read_file_content(WB_PRE_XFORM_PATH)
        def_dict = yaml.safe_load(def_yaml)

        # Unsupported version
        def_dict['version'] = '1.0'
        def_yaml = yaml.safe_dump(def_dict)
        self.assertRaises(Exception, utils.transform_definition, def_yaml)

        # Missing version
        del def_dict['version']
        def_yaml = yaml.safe_dump(def_dict)
        self.assertRaises(Exception, utils.transform_definition, def_yaml)

    def test_transform_workbook_dsl_yaml(self):
        def_yaml = _read_file_content(WB_PRE_XFORM_PATH)
        new_def = utils.transform_definition(def_yaml)
        actual = yaml.safe_load(new_def)
        expected = copy.deepcopy(WB_POST_XFORM_DEF)
        self.assertDictEqual(actual, expected)

    def test_transform_workbook_dsl_dict(self):
        def_yaml = _read_file_content(WB_PRE_XFORM_PATH)
        def_dict = yaml.safe_load(def_yaml)
        actual = utils.transform_definition(def_dict)
        expected = copy.deepcopy(WB_POST_XFORM_DEF)
        self.assertDictEqual(actual, expected)

    def test_transform_workflow_dsl_yaml(self):
        def_yaml = _read_file_content(WF_PRE_XFORM_PATH)
        new_def = utils.transform_definition(def_yaml)
        actual = yaml.safe_load(new_def)
        expected = copy.deepcopy(WF_POST_XFORM_DEF)
        self.assertDictEqual(actual, expected)

    def test_transform_workflow_dsl_dict(self):
        def_yaml = _read_file_content(WF_PRE_XFORM_PATH)
        def_dict = yaml.safe_load(def_yaml)
        actual = utils.transform_definition(def_dict)
        expected = copy.deepcopy(WF_POST_XFORM_DEF)
        self.assertDictEqual(actual, expected)

    def test_deprecated_callback_action(self):
        def_yaml = _read_file_content(WB_PRE_XFORM_PATH)
        def_dict = yaml.safe_load(def_yaml)
        def_dict['workflows']['main']['tasks']['callback'] = {'action': 'st2.callback'}
        def_yaml = yaml.safe_dump(def_dict)
        self.assertRaises(Exception, utils.transform_definition, def_yaml)
