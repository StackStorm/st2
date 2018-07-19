# -*- coding: utf-8 -*-

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

import random
import string

from integration.orchestra import base

from st2common.constants import action as ac_const


class WiringTest(base.TestWorkflowExecution):

    def test_data_flow(self):
        wf_name = 'examples.orchestra-data-flow'
        wf_input = {'a1': 'fee fi fo fum'}

        expected_output = {'a5': wf_input['a1'], 'b5': wf_input['a1']}
        expected_result = {'output': expected_output}

        ex = self._execute_workflow(wf_name, wf_input)
        ex = self._wait_for_completion(ex)

        self.assertEqual(ex.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        self.assertDictEqual(ex.result, expected_result)

    def test_data_flow_unicode(self):
        wf_name = 'examples.orchestra-data-flow'
        wf_input = {'a1': '床前明月光 疑是地上霜 舉頭望明月 低頭思故鄉'}

        expected_output = {
            'a5': wf_input['a1'].decode('utf-8'),
            'b5': wf_input['a1'].decode('utf-8')
        }

        expected_result = {'output': expected_output}

        ex = self._execute_workflow(wf_name, wf_input)
        ex = self._wait_for_completion(ex)

        self.assertEqual(ex.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        self.assertDictEqual(ex.result, expected_result)

    def test_data_flow_big_data_size(self):
        wf_name = 'examples.orchestra-data-flow'

        data_length = 100000
        data = ''.join(random.choice(string.ascii_lowercase) for _ in range(data_length))

        wf_input = {'a1': data}

        expected_output = {'a5': wf_input['a1'], 'b5': wf_input['a1']}
        expected_result = {'output': expected_output}

        ex = self._execute_workflow(wf_name, wf_input)
        ex = self._wait_for_completion(ex)

        self.assertEqual(ex.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        self.assertDictEqual(ex.result, expected_result)
