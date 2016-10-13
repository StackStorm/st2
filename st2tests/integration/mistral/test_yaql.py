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

from st2client import models


class CustomYaqlKeyValuePairTest(base.TestWorkflowExecution):
    secret = None

    @classmethod
    def setUpClass(cls):
        super(CustomYaqlKeyValuePairTest, cls).setUpClass()
        cls.set_kvp('foobar', 'foobar', scope='system', secret=cls.secret)
        cls.set_kvp('marco', 'polo', scope='user', secret=cls.secret)

    @classmethod
    def tearDownClass(cls):
        super(CustomYaqlKeyValuePairTest, cls).tearDownClass()
        cls.del_kvp('foobar')
        cls.del_kvp('marco')

    @classmethod
    def set_kvp(cls, name, value, scope='system', secret=False):
        kvp = models.KeyValuePair(
            id=name,
            name=name,
            value=value,
            scope=scope,
            secret=secret
        )

        cls.st2client.keys.update(kvp)

    @classmethod
    def del_kvp(cls, name, scope='system'):
        kvp = models.KeyValuePair(
            id=name,
            name=name,
            scope=scope
        )

        cls.st2client.keys.delete(kvp)


class UnencryptedKeyValuePairTest(CustomYaqlKeyValuePairTest):
    secret = False

    def test_system_kvp(self):
        execution = self._execute_workflow('examples.mistral-yaql-st2kv-system-scope')
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)

    def test_user_kvp(self):
        execution = self._execute_workflow('examples.mistral-yaql-st2kv-user-scope')
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)


class EncryptedKeyValuePairTest(CustomYaqlKeyValuePairTest):
    secret = True

    def test_system_kvp(self):
        execution = self._execute_workflow('examples.mistral-yaql-st2kv-system-scope')
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)

    def test_user_kvp(self):
        execution = self._execute_workflow('examples.mistral-yaql-st2kv-user-scope')
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
