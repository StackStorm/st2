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

import mock

import st2actions.utils.param_utils as param_utils
from st2common.exceptions import actionrunner
from st2common.models.system.common import ResourceReference
from st2common.models.db.liveaction import LiveActionDB
from st2common.models.db.keyvalue import KeyValuePairDB
from st2common.persistence.keyvalue import KeyValuePair
from st2common.transport.publishers import PoolPublisher
from st2common.util import date as date_utils
from st2tests import DbTestCase
from st2tests.fixturesloader import FixturesLoader


FIXTURES_PACK = 'generic'

TEST_MODELS = {
    'actions': ['action1.yaml', 'action_system_default.yaml'],
    'runners': ['testrunner1.yaml']
}

FIXTURES = FixturesLoader().load_models(fixtures_pack=FIXTURES_PACK,
                                        fixtures_dict=TEST_MODELS)


@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
class ParamsUtilsTest(DbTestCase):
    action_db = FIXTURES['actions']['action1.yaml']
    action_system_default_db = FIXTURES['actions']['action_system_default.yaml']
    runnertype_db = FIXTURES['runners']['testrunner1.yaml']

    def test_get_resolved_params(self):
        params = {
            'actionstr': 'foo',
            'some_key_that_aint_exist_in_action_or_runner': 'bar',
            'runnerint': 555,
            'runnerimmutable': 'failed_override',
            'actionimmutable': 'failed_override'
        }
        liveaction_db = self._get_action_exec_db_model(params)

        runner_params, action_params = param_utils.get_resolved_params(
            ParamsUtilsTest.runnertype_db.runner_parameters,
            ParamsUtilsTest.action_db.parameters,
            liveaction_db.parameters)

        # Asserts for runner params.
        # Assert that default values for runner params are resolved.
        self.assertEqual(runner_params.get('runnerstr'), 'defaultfoo')
        # Assert that a runner param from action exec is picked up.
        self.assertEqual(runner_params.get('runnerint'), 555)
        # Assert that a runner param can be overriden by action param default.
        self.assertEqual(runner_params.get('runnerdummy'), 'actiondummy')
        # Asser that runner param made immutable in action can use default value in runner.
        self.assertEqual(runner_params.get('runnerfoo'), 'FOO')
        # Assert that an immutable param cannot be overriden by action param or execution param.
        self.assertEqual(runner_params.get('runnerimmutable'), 'runnerimmutable')

        # Asserts for action params.
        self.assertEqual(action_params.get('actionstr'), 'foo')
        # Assert that a param that is provided in action exec that isn't in action or runner params
        # isn't in resolved params.
        self.assertEqual(action_params.get('some_key_that_aint_exist_in_action_or_runner'), None)
        # Assert that an immutable param cannot be overriden by execution param.
        self.assertEqual(action_params.get('actionimmutable'), 'actionimmutable')
        # Assert that none of runner params are present in action_params.
        for k in action_params:
            self.assertTrue(k not in runner_params, 'Param ' + k + ' is a runner param.')

    def test_get_finalized_params(self):
        params = {
            'actionstr': 'foo',
            'some_key_that_aint_exist_in_action_or_runner': 'bar',
            'runnerint': 555,
            'runnerimmutable': 'failed_override',
            'actionimmutable': 'failed_override'
        }
        liveaction_db = self._get_action_exec_db_model(params)

        runner_params, action_params = param_utils.get_finalized_params(
            ParamsUtilsTest.runnertype_db.runner_parameters,
            ParamsUtilsTest.action_db.parameters,
            liveaction_db.parameters)

        # Asserts for runner params.
        # Assert that default values for runner params are resolved.
        self.assertEqual(runner_params.get('runnerstr'), 'defaultfoo')
        # Assert that a runner param from action exec is picked up.
        self.assertEqual(runner_params.get('runnerint'), 555)
        # Assert that a runner param can be overriden by action param default.
        self.assertEqual(runner_params.get('runnerdummy'), 'actiondummy')
        # Assert that an immutable param cannot be overriden by action param or execution param.
        self.assertEqual(runner_params.get('runnerimmutable'), 'runnerimmutable')

        # Asserts for action params.
        self.assertEqual(action_params.get('actionstr'), 'foo')
        # Assert that a param that is provided in action exec that isn't in action or runner params
        # isn't in resolved params.
        self.assertEqual(action_params.get('some_key_that_aint_exist_in_action_or_runner'), None)
        # Assert that an immutable param cannot be overriden by execution param.
        self.assertEqual(action_params.get('actionimmutable'), 'actionimmutable')
        # Assert that none of runner params are present in action_params.
        for k in action_params:
            self.assertTrue(k not in runner_params, 'Param ' + k + ' is a runner param.')

    def test_get_finalized_params_system_values(self):
        KeyValuePair.add_or_update(KeyValuePairDB(name='actionstr', value='foo'))
        KeyValuePair.add_or_update(KeyValuePairDB(name='actionnumber', value='1.0'))
        params = {
            'runnerint': 555
        }
        actionexec_db = self._get_action_exec_db_model(params)

        runner_params, action_params = param_utils.get_finalized_params(
            ParamsUtilsTest.runnertype_db.runner_parameters,
            ParamsUtilsTest.action_system_default_db.parameters,
            actionexec_db.parameters)

        # Asserts for runner params.
        # Assert that default values for runner params are resolved.
        self.assertEqual(runner_params.get('runnerstr'), 'defaultfoo')
        # Assert that a runner param from action exec is picked up.
        self.assertEqual(runner_params.get('runnerint'), 555)
        # Assert that an immutable param cannot be overriden by action param or execution param.
        self.assertEqual(runner_params.get('runnerimmutable'), 'runnerimmutable')

        # Asserts for action params.
        self.assertEqual(action_params.get('actionstr'), 'foo')
        self.assertEqual(action_params.get('actionnumber'), 1.0)

    def test_get_resolved_params_action_immutable(self):
        params = {
            'actionstr': 'foo',
            'some_key_that_aint_exist_in_action_or_runner': 'bar',
            'runnerint': 555,
            'actionimmutable': 'failed_override'
        }
        liveaction_db = self._get_action_exec_db_model(params)

        runner_params, action_params = param_utils.get_resolved_params(
            ParamsUtilsTest.runnertype_db.runner_parameters,
            ParamsUtilsTest.action_db.parameters,
            liveaction_db.parameters)

        # Asserts for runner params.
        # Assert that default values for runner params are resolved.
        self.assertEqual(runner_params.get('runnerstr'), 'defaultfoo')
        # Assert that a runner param from action exec is picked up.
        self.assertEqual(runner_params.get('runnerint'), 555)
        # Assert that a runner param can be overriden by action param default.
        self.assertEqual(runner_params.get('runnerdummy'), 'actiondummy')

        # Asserts for action params.
        self.assertEqual(action_params.get('actionstr'), 'foo')
        # Assert that a param that is provided in action exec that isn't in action or runner params
        # isn't in resolved params.
        self.assertEqual(action_params.get('some_key_that_aint_exist_in_action_or_runner'), None)

    def test_get_rendered_params_empty(self):
        runner_params = {}
        action_params = {}
        runner_param_info = {}
        action_param_info = {}
        r_runner_params, r_action_params = param_utils.get_rendered_params(
            runner_params, action_params, runner_param_info, action_param_info)
        self.assertEqual(r_runner_params, runner_params)
        self.assertEqual(r_action_params, action_params)

    def test_get_rendered_params_none(self):
        runner_params = {'r1': None}
        action_params = {'a1': None}
        runner_param_info = {'r1': {}}
        action_param_info = {'a1': {}}
        r_runner_params, r_action_params = param_utils.get_rendered_params(
            runner_params, action_params, runner_param_info, action_param_info)
        self.assertEqual(r_runner_params, runner_params)
        self.assertEqual(r_action_params, action_params)

    def test_get_rendered_params_no_cast(self):
        runner_params = {'r1': '{{r2}}', 'r2': 1}
        action_params = {'a1': True, 'a2': '{{r1}} {{a1}}'}
        runner_param_info = {'r1': {}, 'r2': {}}
        action_param_info = {'a1': {}, 'a2': {}}
        r_runner_params, r_action_params = param_utils.get_rendered_params(
            runner_params, action_params, runner_param_info, action_param_info)
        self.assertEqual(r_runner_params, {'r1': u'1', 'r2': 1})
        self.assertEqual(r_action_params, {'a1': True, 'a2': u'1 True'})

    def test_get_rendered_params_with_cast(self):
        # Note : In this test runner_params.r1 has a string value. However per runner_param_info the
        # type is an integer. The expected type is considered and cast is performed accordingly.
        runner_params = {'r1': '{{r2}}', 'r2': 1}
        action_params = {'a1': True, 'a2': '{{a1}}'}
        runner_param_info = {'r1': {'type': 'integer'}, 'r2': {'type': 'integer'}}
        action_param_info = {'a1': {'type': 'boolean'}, 'a2': {'type': 'boolean'}}
        r_runner_params, r_action_params = param_utils.get_rendered_params(
            runner_params, action_params, runner_param_info, action_param_info)
        self.assertEqual(r_runner_params, {'r1': 1, 'r2': 1})
        self.assertEqual(r_action_params, {'a1': True, 'a2': True})

    def test_unicode_value_casting(self):
        rendered = {'a1': 'unicode1 ٩(̾●̮̮̃̾•̃̾)۶ unicode2'}
        parameter_schemas = {'a1': {'type': 'string'}}

        result = param_utils._cast_params(rendered=rendered,
                                          parameter_schemas=parameter_schemas)
        expected = {
            'a1': (u'unicode1 \xd9\xa9(\xcc\xbe\xe2\x97\x8f\xcc\xae\xcc\xae\xcc'
                   u'\x83\xcc\xbe\xe2\x80\xa2\xcc\x83\xcc\xbe)\xdb\xb6 unicode2')
        }
        self.assertEqual(result, expected)

    def test_get_rendered_params_with_casting_unicode_values(self):
        runner_params = {}
        action_params = {'a1': 'unicode1 ٩(̾●̮̮̃̾•̃̾)۶ unicode2'}

        runner_param_info = {}
        action_param_info = {'a1': {'type': 'string'}}

        r_runner_params, r_action_params = param_utils.get_rendered_params(
            runner_params, action_params, runner_param_info, action_param_info)

        expected_action_params = {
            'a1': (u'unicode1 \xd9\xa9(\xcc\xbe\xe2\x97\x8f\xcc\xae\xcc\xae\xcc'
                   u'\x83\xcc\xbe\xe2\x80\xa2\xcc\x83\xcc\xbe)\xdb\xb6 unicode2')
        }
        self.assertEqual(r_runner_params, {})
        self.assertEqual(r_action_params, expected_action_params)

    def test_get_rendered_params_with_dict(self):
        # Note : In this test runner_params.r1 has a string value. However per runner_param_info the
        # type is an integer. The expected type is considered and cast is performed accordingly.
        runner_params = {'r1': '{{r2}}', 'r2': {'r2.1': 1}}
        action_params = {'a1': True, 'a2': '{{a1}}'}
        runner_param_info = {'r1': {'type': 'object'}, 'r2': {'type': 'object'}}
        action_param_info = {'a1': {'type': 'boolean'}, 'a2': {'type': 'boolean'}}
        r_runner_params, r_action_params = param_utils.get_rendered_params(
            runner_params, action_params, runner_param_info, action_param_info)
        self.assertEqual(r_runner_params, {'r1': {'r2.1': 1}, 'r2': {'r2.1': 1}})
        self.assertEqual(r_action_params, {'a1': True, 'a2': True})

    def test_get_rendered_params_with_list(self):
        # Note : In this test runner_params.r1 has a string value. However per runner_param_info the
        # type is an integer. The expected type is considered and cast is performed accordingly.
        runner_params = {'r1': '{{r2}}', 'r2': ['1', '2']}
        action_params = {'a1': True, 'a2': '{{a1}}'}
        runner_param_info = {'r1': {'type': 'array'}, 'r2': {'type': 'array'}}
        action_param_info = {'a1': {'type': 'boolean'}, 'a2': {'type': 'boolean'}}
        r_runner_params, r_action_params = param_utils.get_rendered_params(
            runner_params, action_params, runner_param_info, action_param_info)
        self.assertEqual(r_runner_params, {'r1': ['1', '2'], 'r2': ['1', '2']})
        self.assertEqual(r_action_params, {'a1': True, 'a2': True})

    def test_get_rendered_params_with_cyclic_dependency(self):
        runner_params = {'r1': '{{r2}}', 'r2': '{{r1}}'}
        test_pass = True
        try:
            param_utils.get_rendered_params(runner_params, {}, {}, {})
            test_pass = False
        except actionrunner.ActionRunnerException as e:
            test_pass = e.message.find('Cyclic') == 0
        self.assertTrue(test_pass)

    def test_get_rendered_params_with_missing_dependency(self):
        runner_params = {'r1': '{{r3}}', 'r2': '{{r3}}'}
        test_pass = True
        try:
            param_utils.get_rendered_params(runner_params, {}, {}, {})
            test_pass = False
        except actionrunner.ActionRunnerException as e:
            test_pass = e.message.find('Dependecy') == 0
        self.assertTrue(test_pass)

    def test_get_rendered_params_param_rendering_failure(self):
        runner_params = {}
        action_params = {'cmd': '{{a2.foo}}', 'a2': 'test'}

        expected_msg = 'Failed to render parameter "cmd": .*'
        self.assertRaisesRegexp(actionrunner.ActionRunnerException,
                                expected_msg,
                                param_utils.get_rendered_params,
                                runner_parameters=runner_params,
                                action_parameters=action_params,
                                runnertype_parameter_info={},
                                action_parameter_info={})

    def _get_action_exec_db_model(self, params):
        liveaction_db = LiveActionDB()
        liveaction_db.status = 'initializing'
        liveaction_db.start_timestamp = date_utils.get_datetime_utc_now()
        liveaction_db.action = ResourceReference(name=ParamsUtilsTest.action_db.name,
                                                 pack=ParamsUtilsTest.action_db.pack).ref
        liveaction_db.parameters = params

        return liveaction_db
