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
import os

import mock

import st2actions.bootstrap.actionsregistrar as actions_registrar
from st2common.persistence.action import Action
from st2common.models.db.action import RunnerTypeDB
import st2tests.base as tests_base

MOCK_RUNNER_TYPE_DB = RunnerTypeDB()
MOCK_RUNNER_TYPE_DB.name = 'run-local'
MOCK_RUNNER_TYPE_DB.runner_module = 'st2.runners.local'


class ActionsRegistrarTest(tests_base.DbTestCase):
    @mock.patch.object(actions_registrar.ActionsRegistrar, '_has_valid_runner_type',
                       mock.MagicMock(return_value=(True, MOCK_RUNNER_TYPE_DB)))
    def test_register_all_actions(self):
        try:
            packs_base_path = os.path.join(tests_base.get_fixtures_path())
            all_actions_in_db = Action.get_all()
            actions_registrar.register_actions(packs_base_path=packs_base_path)
            all_actions_in_db = Action.get_all()
            self.assertTrue(len(all_actions_in_db) > 0)
        except Exception as e:
            print(str(e))
            self.fail('All actions must be registered without exceptions.')

    def test_register_actions_from_bad_pack(self):
        packs_base_path = tests_base.get_fixtures_path()
        try:
            actions_registrar.register_actions(packs_base_path=packs_base_path)
            self.fail('Should have thrown.')
        except:
            pass

    @mock.patch.object(actions_registrar.ActionsRegistrar, '_has_valid_runner_type',
                       mock.MagicMock(return_value=(True, MOCK_RUNNER_TYPE_DB)))
    def test_pack_name_missing(self):
        registrar = actions_registrar.ActionsRegistrar()
        action_file = os.path.join(tests_base.get_fixtures_path(),
                                   'wolfpack/actions/action_3_pack_missing.json')
        registrar._register_action('dummy', action_file)
        action_name = None
        with open(action_file, 'r') as fd:
            content = json.load(fd)
            action_name = str(content['name'])
            action_db = Action.get_by_name(action_name)
            self.assertEqual(action_db.pack, 'dummy', 'Content pack must be ' +
                             'set to dummy')
            Action.delete(action_db)
