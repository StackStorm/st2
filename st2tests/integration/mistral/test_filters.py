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

REGEX_SEARCH_STRINGS = [
    "Your address is 567 Elsewhere Dr. My address is 123 Somewhere Ave.",
    "567 Elsewhere Dr is your address. My address is 123 Somewhere Ave.",
    "No address to be found here! Well, maybe 127.0.0.1"
]


class FromJsonStringFiltersTest(base.TestWorkflowExecution):

    def test_from_json_string(self):

        execution = self._execute_workflow(
            'examples.mistral-test-func-from-json-string',
            parameters={
                "input_str": '{"a": "b"}'
            }
        )
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        jinja_dict = execution.result['result_jinja']
        yaql_dict = execution.result['result_yaql']
        self.assertTrue(isinstance(jinja_dict, dict))
        self.assertEqual(jinja_dict["a"], "b")
        self.assertTrue(isinstance(yaql_dict, dict))
        self.assertEqual(yaql_dict["a"], "b")


class FromYamlStringFiltersTest(base.TestWorkflowExecution):

    def test_to_yaml_string(self):

        execution = self._execute_workflow(
            'examples.mistral-test-func-from-yaml-string',
            parameters={
                "input_str": 'a: b'
            }
        )
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        jinja_dict = execution.result['result_jinja']
        yaql_dict = execution.result['result_yaql']
        self.assertTrue(isinstance(jinja_dict, dict))
        self.assertEqual(jinja_dict["a"], "b")
        self.assertTrue(isinstance(yaql_dict, dict))
        self.assertEqual(yaql_dict["a"], "b")


class JmespathQueryFiltersTest(base.TestWorkflowExecution):

    def test_jmespath_query(self):

        execution = self._execute_workflow(
            'examples.mistral-test-func-jmespath-query',
            parameters={
                "input_obj": {'people': [{'first': 'James', 'last': 'Smith'},
                                         {'first': 'Jacob', 'last': 'Alberts'},
                                         {'first': 'Jayden', 'last': 'Davis'},
                                         {'missing': 'different'}]}
                "input_query": "people[*].last"
            }
        )
        expected_result = ['Smith', 'Alberts', 'Davis']

        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        jinja_result = execution.result['result_jinja']
        yaql_result = execution.result['result_yaql']
        self.assertTrue(isinstance(jinja_result, list))
        self.assertEqual(jinja_result, expected_result)
        self.assertTrue(isinstance(yaql_result, list))
        self.assertEqual(yaql_result, expected_result)


class JsonEscapeFiltersTest(base.TestWorkflowExecution):

    def test_json_escape(self):

        breaking_str = 'This text """ breaks JSON'
        inputs = {'input_str': breaking_str}
        execution = self._execute_workflow(
            'examples.mistral-test-func-json-escape', parameters=inputs
        )
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        jinja_dict = json.loads(execution.result['result_jinja'])[0]
        yaql_dict = json.loads(execution.result['result_yaql'])[0]
        self.assertTrue(isinstance(jinja_dict, dict))
        self.assertEqual(jinja_dict["title"], breaking_str)
        self.assertTrue(isinstance(yaql_dict, dict))
        self.assertEqual(yaql_dict["title"], breaking_str)


class RegexMatchFiltersTest(base.TestWorkflowExecution):

    def test_regex_match(self):

        execution = self._execute_workflow(
            'examples.mistral-test-func-regex-match',
            parameters={
                "input_str": REGEX_SEARCH_STRINGS[1],
                "regex_pattern": "([0-9]{3} \\w+ (?:Ave|St|Dr))"
            }
        )
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        self.assertTrue(execution.result['result_jinja'])
        self.assertTrue(execution.result['result_yaql'])

    def test_regex_nomatch(self):

        execution = self._execute_workflow(
            'examples.mistral-test-func-regex-match',
            parameters={
                "input_str": REGEX_SEARCH_STRINGS[0],
                "regex_pattern": "([0-9]{3} \\w+ (?:Ave|St|Dr))"
            }
        )
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        self.assertFalse(execution.result['result_jinja'])
        self.assertFalse(execution.result['result_yaql'])


class RegexReplaceFiltersTest(base.TestWorkflowExecution):

    def test_regex_replace(self):

        execution = self._execute_workflow(
            'examples.mistral-test-func-regex-replace',
            parameters={
                "input_str": REGEX_SEARCH_STRINGS[1],
                "regex_pattern": "([0-9]{3} \\w+ (?:Ave|St|Dr))",
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

        execution = self._execute_workflow(
            'examples.mistral-test-func-regex-search',
            parameters={
                "input_str": REGEX_SEARCH_STRINGS[0],
                "regex_pattern": "([0-9]{3} \\w+ (?:Ave|St|Dr))"
            }
        )
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        self.assertTrue(execution.result['result_jinja'])
        self.assertTrue(execution.result['result_yaql'])

    def test_regex_nosearch(self):

        execution = self._execute_workflow(
            'examples.mistral-test-func-regex-search',
            parameters={
                "input_str": REGEX_SEARCH_STRINGS[2],
                "regex_pattern": "([0-9]{3} \\w+ (?:Ave|St|Dr))"
            }
        )
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        self.assertFalse(execution.result['result_jinja'])
        self.assertFalse(execution.result['result_yaql'])


class RegexSubstringFiltersTest(base.TestWorkflowExecution):

    def test_regex_substring(self):

        execution = self._execute_workflow(
            'examples.mistral-test-func-regex-substring',
            parameters={
                "input_str": REGEX_SEARCH_STRINGS[0],
                "regex_pattern": "([0-9]{3} \\w+ (?:Ave|St|Dr))"
            }
        )
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        self.assertEqual(execution.result['result_jinja'], '567 Elsewhere Dr')
        self.assertEqual(execution.result['result_yaql'], '567 Elsewhere Dr')
        self.assertEqual(execution.result['result_jinja_index_1'], '123 Somewhere Ave')
        self.assertEqual(execution.result['result_yaql_index_1'], '123 Somewhere Ave')


class ToHumanTimeFromSecondsFiltersTest(base.TestWorkflowExecution):

    def test_to_human_time_from_seconds(self):

        execution = self._execute_workflow(
            'examples.mistral-test-func-to-human-time-from-seconds',
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
            'examples.mistral-test-func-use-none', parameters=inputs
        )
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=2)
        self.assertEqual(execution.result['none_result_jinja'], '%*****__%NONE%__*****%')
        self.assertEqual(execution.result['none_result_yaql'], '%*****__%NONE%__*****%')
        self.assertEqual(execution.result['str_result_jinja'], 'foo')
        self.assertEqual(execution.result['str_result_yaql'], 'foo')


class ToComplexFiltersTest(base.TestWorkflowExecution):

    def test_to_complex(self):

        execution = self._execute_workflow(
            'examples.mistral-test-func-to-complex',
            parameters={
                "input_obj": {"a": "b"}
            }
        )
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        jinja_dict = json.loads(execution.result['result_jinja'])
        yaql_dict = json.loads(execution.result['result_yaql'])
        self.assertTrue(isinstance(jinja_dict, dict))
        self.assertEqual(jinja_dict["a"], "b")
        self.assertTrue(isinstance(yaql_dict, dict))
        self.assertEqual(yaql_dict["a"], "b")


class ToJsonStringFiltersTest(base.TestWorkflowExecution):

    def test_to_json_string(self):

        execution = self._execute_workflow(
            'examples.mistral-test-func-to-json-string',
            parameters={
                "input_obj": {"a": "b"}
            }
        )
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        jinja_dict = json.loads(execution.result['result_jinja'])
        yaql_dict = json.loads(execution.result['result_yaql'])
        self.assertTrue(isinstance(jinja_dict, dict))
        self.assertEqual(jinja_dict["a"], "b")
        self.assertTrue(isinstance(yaql_dict, dict))
        self.assertEqual(yaql_dict["a"], "b")


class ToYamlStringFiltersTest(base.TestWorkflowExecution):

    def test_to_yaml_string(self):

        execution = self._execute_workflow(
            'examples.mistral-test-func-to-yaml-string',
            parameters={
                "input_obj": {"a": "b"}
            }
        )
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        jinja_dict = yaml.load(execution.result['result_jinja'])
        yaql_dict = yaml.load(execution.result['result_yaql'])
        self.assertTrue(isinstance(jinja_dict, dict))
        self.assertEqual(jinja_dict["a"], "b")
        self.assertTrue(isinstance(yaql_dict, dict))
        self.assertEqual(yaql_dict["a"], "b")


class VersionCompareFiltersTest(base.TestWorkflowExecution):

    def test_version_compare(self):

        versions = {
            '0.9.3': 1,
            '0.10.1': 0,
            '0.10.2': -1
        }
        for compare_version, expected_result in versions.items():
            execution = self._execute_workflow(
                'examples.mistral-test-func-version-compare',
                parameters={
                    "version_a": '0.10.1',
                    "version_b": compare_version
                }
            )
            execution = self._wait_for_completion(execution)
            self._assert_success(execution, num_tasks=1)
            self.assertEqual(execution.result['result_jinja'], expected_result)
            self.assertEqual(execution.result['result_yaql'], expected_result)


class VersionMoreThanFiltersTest(base.TestWorkflowExecution):

    def test_version_more_than(self):

        versions = {
            '0.9.3': True,
            '0.10.1': False,
            '0.10.2': False
        }
        for compare_version, expected_result in versions.items():
            execution = self._execute_workflow(
                'examples.mistral-test-func-version-more-than',
                parameters={
                    "version_a": '0.10.1',
                    "version_b": compare_version
                }
            )
            execution = self._wait_for_completion(execution)
            self._assert_success(execution, num_tasks=1)
            self.assertEqual(execution.result['result_jinja'], expected_result)
            self.assertEqual(execution.result['result_yaql'], expected_result)


class VersionLessThanFiltersTest(base.TestWorkflowExecution):

    def test_version_less_than(self):

        versions = {
            '0.9.3': False,
            '0.10.1': False,
            '0.10.2': True
        }
        for compare_version, expected_result in versions.items():
            execution = self._execute_workflow(
                'examples.mistral-test-func-version-less-than',
                parameters={
                    "version_a": '0.10.1',
                    "version_b": compare_version
                }
            )
            execution = self._wait_for_completion(execution)
            self._assert_success(execution, num_tasks=1)
            self.assertEqual(execution.result['result_jinja'], expected_result)
            self.assertEqual(execution.result['result_yaql'], expected_result)


class VersionEqualFiltersTest(base.TestWorkflowExecution):

    def test_version_equal(self):

        versions = {
            '0.9.3': False,
            '0.10.1': True,
            '0.10.2': False
        }
        for compare_version, expected_result in versions.items():
            execution = self._execute_workflow(
                'examples.mistral-test-func-version-equal',
                parameters={
                    "version_a": '0.10.1',
                    "version_b": compare_version
                }
            )
            execution = self._wait_for_completion(execution)
            self._assert_success(execution, num_tasks=1)
            self.assertEqual(execution.result['result_jinja'], expected_result)
            self.assertEqual(execution.result['result_yaql'], expected_result)


class VersionMatchFiltersTest(base.TestWorkflowExecution):

    def test_version_match(self):

        versions = {
            '>=0.9.3': True,
            '>0.11.3': False,
            '==0.9.3': False,
            '<=0.10.1': True,
            '<0.10.2': True
        }
        for compare_version, expected_result in versions.items():
            execution = self._execute_workflow(
                'examples.mistral-test-func-version-match',
                parameters={
                    "version_a": '0.10.1',
                    "version_b": compare_version
                }
            )
            execution = self._wait_for_completion(execution)
            self._assert_success(execution, num_tasks=1)
            self.assertEqual(execution.result['result_jinja'], expected_result)
            self.assertEqual(execution.result['result_yaql'], expected_result)


class VersionBumpMajorFiltersTest(base.TestWorkflowExecution):

    def test_version_bump_major(self):

        execution = self._execute_workflow(
            'examples.mistral-test-func-version-bump-major',
            parameters={
                "version": '0.10.1'
            }
        )
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        self.assertEqual(execution.result['result_jinja'], '1.0.0')
        self.assertEqual(execution.result['result_yaql'], '1.0.0')


class VersionBumpMinorFiltersTest(base.TestWorkflowExecution):

    def test_version_bump_minor(self):

        execution = self._execute_workflow(
            'examples.mistral-test-func-version-bump-minor',
            parameters={
                "version": '0.10.1'
            }
        )
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        self.assertEqual(execution.result['result_jinja'], '0.11.0')
        self.assertEqual(execution.result['result_yaql'], '0.11.0')


class VersionBumpPatchFiltersTest(base.TestWorkflowExecution):

    def test_version_bump_patch(self):

        execution = self._execute_workflow(
            'examples.mistral-test-func-version-bump-patch',
            parameters={
                "version": '0.10.1'
            }
        )
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        self.assertEqual(execution.result['result_jinja'], '0.10.2')
        self.assertEqual(execution.result['result_yaql'], '0.10.2')


class VersionStripPatchFiltersTest(base.TestWorkflowExecution):

    def test_version_strip_patch(self):

        execution = self._execute_workflow(
            'examples.mistral-test-func-version-strip-patch',
            parameters={
                "version": '0.10.1'
            }
        )
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        self.assertEqual(execution.result['result_jinja'], '0.10')
        self.assertEqual(execution.result['result_yaql'], '0.10')
