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

from integration.mistral import base


class JinjaFiltersTest(base.TestWorkflowExecution):
    """This set of tests ensures that StackStorm's custom Jinja filters work in Mistral workflows
    """

    def test_usenone(self):
        """ if input is None, replace with string: '%*****__%NONE%__*****%'
        """

        inputs = {'inputstr': None}
        execution = self._execute_workflow(
            'examples.mistral-customfilter-usenone', parameters=inputs
        )
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        self.assertEqual(len(execution.result['result']['stdout']), '%*****__%NONE%__*****%')
