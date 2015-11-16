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

import mock

from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED
from st2common.services import action as action_service
from st2tests.fixturesloader import FixturesLoader
from tests import FunctionalTest

FIXTURES_PACK = 'aliases'

TEST_MODELS = {
    'aliases': ['alias1.yaml', 'alias2.yaml'],
    'actions': ['action1.yaml'],
    'runners': ['runner1.yaml']
}

TEST_LOAD_MODELS = {
    'aliases': ['alias3.yaml']
}

__all__ = [
    'AliasExecutionTestCase'
]


class DummyActionExecution(object):
    def __init__(self, id_=None, status=LIVEACTION_STATUS_SUCCEEDED, result=''):
        self.id = id_
        self.status = status
        self.result = result


class AliasExecutionTestCase(FunctionalTest):

    models = None
    alias1 = None
    alias2 = None

    @classmethod
    def setUpClass(cls):
        super(TestAliasExecution, cls).setUpClass()
        cls.models = FixturesLoader().save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                                          fixtures_dict=TEST_MODELS)
        cls.alias1 = cls.models['aliases']['alias1.yaml']
        cls.alias2 = cls.models['aliases']['alias2.yaml']

    @mock.patch.object(action_service, 'request',
                       return_value=(None, DummyActionExecution(id_=1)))
    def test_basic_execution(self, request):
        command = 'Lorem ipsum value1 dolor sit "value2 value3" amet.'
        post_resp = self._do_post(alias_execution=self.alias1, command=command)
        self.assertEqual(post_resp.status_int, 200)
        expected_parameters = {'param1': 'value1', 'param2': 'value2 value3'}
        self.assertEquals(request.call_args[0][0].parameters, expected_parameters)

    @mock.patch.object(action_service, 'request',
                       return_value=(None, DummyActionExecution(id_=1)))
    def test_execution_with_array_type_single_value(self, request):
        command = 'Lorem ipsum value1 dolor sit value2 amet.'
        post_resp = self._do_post(alias_execution=self.alias2, command=command)
        self.assertEqual(post_resp.status_int, 200)
        expected_parameters = {'param1': 'value1', 'param3': ['value2']}
        self.assertEquals(request.call_args[0][0].parameters, expected_parameters)

    @mock.patch.object(action_service, 'request',
                       return_value=(None, DummyActionExecution(id_=1)))
    def test_execution_with_array_type_multi_value(self, request):
        command = 'Lorem ipsum value1 dolor sit "value2, value3" amet.'
        post_resp = self._do_post(alias_execution=self.alias2, command=command)
        self.assertEqual(post_resp.status_int, 200)
        expected_parameters = {'param1': 'value1', 'param3': ['value2', 'value3']}
        self.assertEquals(request.call_args[0][0].parameters, expected_parameters)

    def _do_post(self, alias_execution, command, expect_errors=False):
        execution = {'name': alias_execution.name,
                     'format': alias_execution.formats[0],
                     'command': command,
                     'user': 'stanley',
                     'source_channel': 'test',
                     'notification_route': 'test'}
        return self.app.post_json('/v1/aliasexecution', execution,
                                  expect_errors=expect_errors)
