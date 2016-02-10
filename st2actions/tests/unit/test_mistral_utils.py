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

import unittest2

from st2actions.handlers.mistral import get_action_execution_id_from_url


class MistralUtilityTest(unittest2.TestCase):

    def test_get_action_execution_id_from_url(self):
        self.assertEqual(
            '12345',
            get_action_execution_id_from_url('http://127.0.0.1:8989/v2/action_executions/12345'))

        self.assertRaises(
            ValueError,
            get_action_execution_id_from_url,
            'http://127.0.0.1:8989/v2/action_executions')

        self.assertRaises(
            ValueError,
            get_action_execution_id_from_url,
            '/action_executions/12345')

        self.assertRaises(
            ValueError,
            get_action_execution_id_from_url,
            '/action_executions')

        self.assertRaises(
            ValueError,
            get_action_execution_id_from_url,
            'http://127.0.0.1:8989/v2/workflows/abcde')
