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
from st2common.models.db.execution import ActionExecutionDB
from st2common.services import action as action_service
from st2tests.fixturesloader import FixturesLoader
from tests import FunctionalTest

FIXTURES_PACK = 'aliases'

TEST_MODELS = {
    'aliases': ['alias1.yaml', 'alias2.yaml', 'alias_with_undefined_jinja_in_ack_format.yaml'],
    'actions': ['action1.yaml'],
    'runners': ['runner1.yaml']
}

TEST_LOAD_MODELS = {
    'aliases': ['alias3.yaml']
}

EXECUTION = ActionExecutionDB(id='54e657d60640fd16887d6855',
                              status=LIVEACTION_STATUS_SUCCEEDED,
                              result='')

__all__ = [
    'AliasExecutionTestCase'
]


class AliasExecutionTestCase(FunctionalTest):

    models = None
    alias1 = None
    alias2 = None
    alias_with_undefined_jinja_in_ack_format = None

    @classmethod
    def setUpClass(cls):
        super(AliasExecutionTestCase, cls).setUpClass()
        cls.models = FixturesLoader().save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                                          fixtures_dict=TEST_MODELS)
        cls.alias1 = cls.models['aliases']['alias1.yaml']
        cls.alias2 = cls.models['aliases']['alias2.yaml']
        cls.alias_with_undefined_jinja_in_ack_format = \
            cls.models['aliases']['alias_with_undefined_jinja_in_ack_format.yaml']

    @mock.patch.object(action_service, 'request',
                       return_value=(None, EXECUTION))
    def test_basic_execution(self, request):
        command = 'Lorem ipsum value1 dolor sit "value2 value3" amet.'
        post_resp = self._do_post(alias_execution=self.alias1, command=command)
        self.assertEqual(post_resp.status_int, 201)
        expected_parameters = {'param1': 'value1', 'param2': 'value2 value3'}
        self.assertEquals(request.call_args[0][0].parameters, expected_parameters)

    @mock.patch.object(action_service, 'request',
                       return_value=(None, EXECUTION))
    def test_invalid_format_string_referenced_in_request(self, request):
        command = 'Lorem ipsum value1 dolor sit "value2 value3" amet.'
        format_str = 'some invalid not supported string'
        post_resp = self._do_post(alias_execution=self.alias1, command=command,
                                  format_str=format_str, expect_errors=True)
        self.assertEqual(post_resp.status_int, 400)
        expected_msg = ('Format string "some invalid not supported string" is '
                        'not available on the alias "alias1"')
        self.assertTrue(expected_msg in post_resp.json['faultstring'])

    @mock.patch.object(action_service, 'request',
                       return_value=(None, EXECUTION))
    def test_execution_with_array_type_single_value(self, request):
        command = 'Lorem ipsum value1 dolor sit value2 amet.'
        post_resp = self._do_post(alias_execution=self.alias2, command=command)
        self.assertEqual(post_resp.status_int, 201)
        expected_parameters = {'param1': 'value1', 'param3': ['value2']}
        self.assertEquals(request.call_args[0][0].parameters, expected_parameters)

    @mock.patch.object(action_service, 'request',
                       return_value=(None, EXECUTION))
    def test_execution_with_array_type_multi_value(self, request):
        command = 'Lorem ipsum value1 dolor sit "value2, value3" amet.'
        post_resp = self._do_post(alias_execution=self.alias2, command=command)
        self.assertEqual(post_resp.status_int, 201)
        expected_parameters = {'param1': 'value1', 'param3': ['value2', 'value3']}
        self.assertEquals(request.call_args[0][0].parameters, expected_parameters)

    @mock.patch.object(action_service, 'request',
                       return_value=(None, EXECUTION))
    def test_invalid_jinja_var_in_ack_format(self, request):
        command = 'run date on localhost'
        # print(self.alias_with_undefined_jinja_in_ack_format)
        post_resp = self._do_post(
            alias_execution=self.alias_with_undefined_jinja_in_ack_format,
            command=command,
            expect_errors=False
        )
        self.assertEqual(post_resp.status_int, 201)
        expected_parameters = {'cmd': 'date', 'hosts': 'localhost'}
        self.assertEquals(request.call_args[0][0].parameters, expected_parameters)
        self.assertEqual(
            post_resp.json['message'],
            'Cannot render "format" in field "ack" for alias. \'cmd\' is undefined'
        )

    def _do_post(self, alias_execution, command, format_str=None, expect_errors=False):
        if (isinstance(alias_execution.formats[0], dict) and
           alias_execution.formats[0].get('representation')):
            representation = alias_execution.formats[0].get('representation')[0]
        else:
            representation = alias_execution.formats[0]

        if not format_str:
            format_str = representation

        execution = {'name': alias_execution.name,
                     'format': format_str,
                     'command': command,
                     'user': 'stanley',
                     'source_channel': 'test',
                     'notification_route': 'test'}
        return self.app.post_json('/v1/aliasexecution', execution,
                                  expect_errors=expect_errors)
