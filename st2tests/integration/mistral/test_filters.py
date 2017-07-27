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

import json
import yaml

from integration.mistral import base

REGEX_SEARCH_STR = "Your address is 567 Elsewhere Dr. My address is 123 Somewhere Ave."
REGEX_SEARCH_STR_2 = "567 Elsewhere Dr is your address. My address is 123 Somewhere Ave."
REGEX_SEARCH_STR_3 = "No address to be found here! Well, maybe 127.0.0.1"


class RegexMatchFiltersTest(base.TestWorkflowExecution):

    def test_regex_match(self):
        execution = self._execute_workflow('examples.mistral-customfilters-regex_match',
                                           parameters={"input_str": REGEX_SEARCH_STR_2})
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        self.assertTrue(execution.result['result_jinja'])
        self.assertTrue(execution.result['result_yaql'])

    def test_regex_nomatch(self):
        execution = self._execute_workflow('examples.mistral-customfilters-regex_match',
                                           parameters={"input_str": REGEX_SEARCH_STR})
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        self.assertFalse(execution.result['result_jinja'])
        self.assertFalse(execution.result['result_yaql'])


class RegexReplaceFiltersTest(base.TestWorkflowExecution):

    def test_regex_replace(self):
        execution = self._execute_workflow(
            'examples.mistral-customfilters-regex_replace',
            parameters={
                "input_str": REGEX_SEARCH_STR_2,
                "replacement_str": "foo"
            }
        )
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        self.assertEqual(
            execution.result['result_jinja'],
            "foo is your address. My address is foo."
        )
        self.assertEqual(execution.result['result_yaql'], "foo is your address. My address is foo.")


class RegexSearchFiltersTest(base.TestWorkflowExecution):

    def test_regex_search(self):
        execution = self._execute_workflow('examples.mistral-customfilters-regex_search',
                                           parameters={"input_str": REGEX_SEARCH_STR})
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        self.assertTrue(execution.result['result_jinja'])
        self.assertTrue(execution.result['result_yaql'])

    def test_regex_nosearch(self):
        execution = self._execute_workflow('examples.mistral-customfilters-regex_search',
                                           parameters={"input_str": REGEX_SEARCH_STR_3})
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        self.assertFalse(execution.result['result_jinja'])
        self.assertFalse(execution.result['result_yaql'])


class RegexSubstringFiltersTest(base.TestWorkflowExecution):

    def test_regex_substring(self):
        execution = self._execute_workflow('examples.mistral-customfilters-regex_substring',
                                           parameters={"input_str": REGEX_SEARCH_STR})
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        self.assertEqual(execution.result['result_jinja'], '567 Elsewhere Dr')
        self.assertEqual(execution.result['result_yaql'], '567 Elsewhere Dr')
        self.assertEqual(execution.result['result_jinja_index_1'], '123 Somewhere Ave')
        self.assertEqual(execution.result['result_yaql_index_1'], '123 Somewhere Ave')


class ToHumanTimeInSecondsFiltersTest(base.TestWorkflowExecution):

    def test_to_human_time_in_seconds(self):
        execution = self._execute_workflow(
            'examples.mistral-customfilters-to_human_time_from_seconds',
            parameters={"seconds": 4587}
        )
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        self.assertEqual(execution.result['result_jinja'], '1h16m27s')
        self.assertEqual(execution.result['result_yaql'], '1h16m27s')


class UseNoneFiltersTest(base.TestWorkflowExecution):

    def test_use_none(self):
        inputs = {'input_str': 'foo'}
        execution = self._execute_workflow(
            'examples.mistral-customfilters-use_none', parameters=inputs
        )
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=2)
        self.assertEqual(execution.result['none_result_jinja'], '%*****__%NONE%__*****%')
        self.assertEqual(execution.result['none_result_yaql'], '%*****__%NONE%__*****%')
        self.assertEqual(execution.result['str_result_jinja'], 'foo')
        self.assertEqual(execution.result['str_result_yaql'], 'foo')


class ToJsonStringFiltersTest(base.TestWorkflowExecution):

    def test_to_json_string(self):
        execution = self._execute_workflow(
            'examples.mistral-customfilters-to_json_string'
        )
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=2)
        jinja_dict = json.loads(execution.result['result_jinja'])
        yaql_dict = json.loads(execution.result['result_yaql'])
        self.assertTrue(isinstance(jinja_dict, dict))
        self.assertEqual(jinja_dict["a"], "b")
        self.assertTrue(isinstance(yaql_dict, dict))
        self.assertEqual(yaql_dict["a"], "b")


class ToYamlStringFiltersTest(base.TestWorkflowExecution):

    def test_to_yaml_string(self):
        execution = self._execute_workflow(
            'examples.mistral-customfilters-to_yaml_string'
        )
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=2)
        jinja_dict = yaml.load(execution.result['result_jinja'])
        yaql_dict = yaml.load(execution.result['result_yaql'])
        self.assertTrue(isinstance(jinja_dict, dict))
        self.assertEqual(jinja_dict["a"], "b")
        self.assertTrue(isinstance(yaql_dict, dict))
        self.assertEqual(yaql_dict["a"], "b")


class ToComplexFiltersTest(base.TestWorkflowExecution):

    def test_to_complex(self):
        execution = self._execute_workflow(
            'examples.mistral-customfilters-to_complex'
        )
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=2)
        jinja_dict = json.loads(execution.result['result_jinja'])
        yaql_dict = json.loads(execution.result['result_yaql'])
        self.assertTrue(isinstance(jinja_dict, dict))
        self.assertEqual(jinja_dict["a"], "b")
        self.assertTrue(isinstance(yaql_dict, dict))
        self.assertEqual(yaql_dict["a"], "b")


class JsonEscapeFiltersTest(base.TestWorkflowExecution):

    def test_to_complex(self):
        breaking_str = 'This text """ breaks JSON'
        inputs = {'input_str': breaking_str}
        execution = self._execute_workflow(
            'examples.mistral-customfilters-json_escape', parameters=inputs
        )
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        jinja_dict = json.loads(execution.result['result_jinja'])[0]
        yaql_dict = json.loads(execution.result['result_yaql'])[0]
        self.assertTrue(isinstance(jinja_dict, dict))
        self.assertEqual(jinja_dict["title"], breaking_str)
        self.assertTrue(isinstance(yaql_dict, dict))
        self.assertEqual(yaql_dict["title"], breaking_str)
