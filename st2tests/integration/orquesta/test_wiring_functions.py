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

from integration.orquesta import base

from st2common.constants import action as ac_const


class FunctionsWiringTest(base.TestWorkflowExecution):

    def test_data_functions_in_yaql(self):
        wf_name = 'examples.orquesta-test-yaql-data-functions'

        expected_output = {
            'data_json_str_1': '{"foo": "bar"}',
            'data_json_str_2': '{"foo": "bar"}',
            'data_json_obj_1': {'foo': 'bar'},
            'data_json_obj_2': {'foo': 'bar'},
            'data_yaml_str_1': 'foo: bar\n'
        }

        expected_result = {'output': expected_output}

        ex = self._execute_workflow(wf_name)
        ex = self._wait_for_completion(ex)

        self.assertEqual(ex.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        self.assertDictEqual(ex.result, expected_result)

    def test_data_functions_in_jinja(self):
        wf_name = 'examples.orquesta-test-jinja-data-functions'

        expected_output = {
            'data_json_str_1': '{"foo": "bar"}',
            'data_json_str_2': '{"foo": "bar"}',
            'data_json_obj_1': {'foo': 'bar'},
            'data_json_obj_2': {'foo': 'bar'},
            'data_yaml_str_1': 'foo: bar\n',
            'data_pipe_str_1': '{"foo": "bar"}'
        }

        expected_result = {'output': expected_output}

        ex = self._execute_workflow(wf_name)
        ex = self._wait_for_completion(ex)

        self.assertEqual(ex.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        self.assertDictEqual(ex.result, expected_result)
