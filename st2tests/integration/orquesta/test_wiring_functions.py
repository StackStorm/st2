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


class FunctionsWiringTest(base.TestWorkflowExecution):

    def test_data_functions_in_yaql(self):
        wf_name = 'examples.orquesta-test-yaql-data-functions'

        expected_output = {
            'data_json_str_1': '{"foo": {"bar": "foobar"}}',
            'data_json_str_2': '{"foo": {"bar": "foobar"}}',
            'data_json_obj_1': {'foo': {'bar': 'foobar'}},
            'data_json_obj_2': {'foo': {'bar': 'foobar'}},
            'data_yaml_str_1': 'foo:\n  bar: foobar\n',
            'data_query_1': ['foobar']
        }

        expected_result = {'output': expected_output}

        self._execute_workflow(wf_name, execute_async=False, expected_result=expected_result)

    def test_data_functions_in_jinja(self):
        wf_name = 'examples.orquesta-test-jinja-data-functions'

        expected_output = {
            'data_json_str_1': '{"foo": {"bar": "foobar"}}',
            'data_json_str_2': '{"foo": {"bar": "foobar"}}',
            'data_json_obj_1': {'foo': {'bar': 'foobar'}},
            'data_json_obj_2': {'foo': {'bar': 'foobar'}},
            'data_yaml_str_1': 'foo:\n  bar: foobar\n',
            'data_query_1': ['foobar'],
            'data_pipe_str_1': '{"foo": {"bar": "foobar"}}'
        }

        expected_result = {'output': expected_output}

        self._execute_workflow(wf_name, execute_async=False, expected_result=expected_result)

    def test_regex_functions_in_yaql(self):
        wf_name = 'examples.orquesta-test-yaql-regex-functions'

        expected_output = {
            'match': True,
            'replace': 'wxyz',
            'search': True,
            'substring': '668 Infinite Dr'
        }

        expected_result = {'output': expected_output}

        self._execute_workflow(wf_name, execute_async=False, expected_result=expected_result)

    def test_regex_functions_in_jinja(self):
        wf_name = 'examples.orquesta-test-jinja-regex-functions'

        expected_output = {
            'match': True,
            'replace': 'wxyz',
            'search': True,
            'substring': '668 Infinite Dr'
        }

        expected_result = {'output': expected_output}

        self._execute_workflow(wf_name, execute_async=False, expected_result=expected_result)

    def test_version_functions_in_yaql(self):
        wf_name = 'examples.orquesta-test-yaql-version-functions'

        expected_output = {
            'compare_equal': 0,
            'compare_more_than': -1,
            'compare_less_than': 1,
            'equal': True,
            'more_than': False,
            'less_than': False,
            'match': True,
            'bump_major': '1.0.0',
            'bump_minor': '0.11.0',
            'bump_patch': '0.10.1',
            'strip_patch': '0.10'
        }

        expected_result = {'output': expected_output}

        self._execute_workflow(wf_name, execute_async=False, expected_result=expected_result)

    def test_version_functions_in_jinja(self):
        wf_name = 'examples.orquesta-test-jinja-version-functions'

        expected_output = {
            'compare_equal': 0,
            'compare_more_than': -1,
            'compare_less_than': 1,
            'equal': True,
            'more_than': False,
            'less_than': False,
            'match': True,
            'bump_major': '1.0.0',
            'bump_minor': '0.11.0',
            'bump_patch': '0.10.1',
            'strip_patch': '0.10'
        }

        expected_result = {'output': expected_output}

        self._execute_workflow(wf_name, execute_async=False, expected_result=expected_result)
