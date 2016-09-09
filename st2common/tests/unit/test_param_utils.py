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

from st2common.exceptions.param import ParamException
from st2common.models.system.common import ResourceReference
from st2common.models.db.liveaction import LiveActionDB
from st2common.models.db.keyvalue import KeyValuePairDB
from st2common.models.utils import action_param_utils
from st2common.persistence.keyvalue import KeyValuePair
from st2common.transport.publishers import PoolPublisher
from st2common.util import date as date_utils
from st2common.util import param as param_utils
from st2tests import DbTestCase
from st2tests.fixturesloader import FixturesLoader


FIXTURES_PACK = 'generic'

TEST_MODELS = {
    'actions': ['action_4_action_context_param.yaml', 'action_system_default.yaml'],
    'runners': ['testrunner1.yaml']
}

FIXTURES = FixturesLoader().load_models(fixtures_pack=FIXTURES_PACK,
                                        fixtures_dict=TEST_MODELS)


@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
class ParamsUtilsTest(DbTestCase):
    action_db = FIXTURES['actions']['action_4_action_context_param.yaml']
    action_system_default_db = FIXTURES['actions']['action_system_default.yaml']
    runnertype_db = FIXTURES['runners']['testrunner1.yaml']

    def test_get_finalized_params(self):
        params = {
            'actionstr': 'foo',
            'some_key_that_aint_exist_in_action_or_runner': 'bar',
            'runnerint': 555,
            'runnerimmutable': 'failed_override',
            'actionimmutable': 'failed_override'
        }
        liveaction_db = self._get_liveaction_model(params)

        runner_params, action_params = param_utils.get_finalized_params(
            ParamsUtilsTest.runnertype_db.runner_parameters,
            ParamsUtilsTest.action_db.parameters,
            liveaction_db.parameters,
            liveaction_db.context)

        # Asserts for runner params.
        # Assert that default values for runner params are resolved.
        self.assertEqual(runner_params.get('runnerstr'), 'defaultfoo')
        # Assert that a runner param from action exec is picked up.
        self.assertEqual(runner_params.get('runnerint'), 555)
        # Assert that a runner param can be overridden by action param default.
        self.assertEqual(runner_params.get('runnerdummy'), 'actiondummy')
        # Assert that a runner param default can be overridden by 'falsey' action param default,
        # (timeout: 0 case).
        self.assertEqual(runner_params.get('runnerdefaultint'), 0)
        # Assert that an immutable param cannot be overridden by action param or execution param.
        self.assertEqual(runner_params.get('runnerimmutable'), 'runnerimmutable')

        # Asserts for action params.
        self.assertEqual(action_params.get('actionstr'), 'foo')
        # Assert that a param that is provided in action exec that isn't in action or runner params
        # isn't in resolved params.
        self.assertEqual(action_params.get('some_key_that_aint_exist_in_action_or_runner'), None)
        # Assert that an immutable param cannot be overridden by execution param.
        self.assertEqual(action_params.get('actionimmutable'), 'actionimmutable')
        # Assert that an action context param is set correctly.
        self.assertEqual(action_params.get('action_api_user'), 'noob')
        # Assert that none of runner params are present in action_params.
        for k in action_params:
            self.assertTrue(k not in runner_params, 'Param ' + k + ' is a runner param.')

    def test_get_finalized_params_system_values(self):
        KeyValuePair.add_or_update(KeyValuePairDB(name='actionstr', value='foo'))
        KeyValuePair.add_or_update(KeyValuePairDB(name='actionnumber', value='1.0'))
        params = {
            'runnerint': 555
        }
        liveaction_db = self._get_liveaction_model(params)

        runner_params, action_params = param_utils.get_finalized_params(
            ParamsUtilsTest.runnertype_db.runner_parameters,
            ParamsUtilsTest.action_system_default_db.parameters,
            liveaction_db.parameters,
            liveaction_db.context)

        # Asserts for runner params.
        # Assert that default values for runner params are resolved.
        self.assertEqual(runner_params.get('runnerstr'), 'defaultfoo')
        # Assert that a runner param from action exec is picked up.
        self.assertEqual(runner_params.get('runnerint'), 555)
        # Assert that an immutable param cannot be overridden by action param or execution param.
        self.assertEqual(runner_params.get('runnerimmutable'), 'runnerimmutable')

        # Asserts for action params.
        self.assertEqual(action_params.get('actionstr'), 'foo')
        self.assertEqual(action_params.get('actionnumber'), 1.0)

    def test_get_finalized_params_action_immutable(self):
        params = {
            'actionstr': 'foo',
            'some_key_that_aint_exist_in_action_or_runner': 'bar',
            'runnerint': 555,
            'actionimmutable': 'failed_override'
        }
        liveaction_db = self._get_liveaction_model(params)
        action_context = {'api_user': None}

        runner_params, action_params = param_utils.get_finalized_params(
            ParamsUtilsTest.runnertype_db.runner_parameters,
            ParamsUtilsTest.action_db.parameters,
            liveaction_db.parameters,
            action_context)

        # Asserts for runner params.
        # Assert that default values for runner params are resolved.
        self.assertEqual(runner_params.get('runnerstr'), 'defaultfoo')
        # Assert that a runner param from action exec is picked up.
        self.assertEqual(runner_params.get('runnerint'), 555)
        # Assert that a runner param can be overridden by action param default.
        self.assertEqual(runner_params.get('runnerdummy'), 'actiondummy')

        # Asserts for action params.
        self.assertEqual(action_params.get('actionstr'), 'foo')
        # Assert that a param that is provided in action exec that isn't in action or runner params
        # isn't in resolved params.
        self.assertEqual(action_params.get('some_key_that_aint_exist_in_action_or_runner'), None)

    def test_get_finalized_params_empty(self):
        params = {}
        runner_param_info = {}
        action_param_info = {}
        action_context = {}
        r_runner_params, r_action_params = param_utils.get_finalized_params(
            runner_param_info, action_param_info, params, action_context)
        self.assertEqual(r_runner_params, params)
        self.assertEqual(r_action_params, params)

    def test_get_finalized_params_none(self):
        params = {
            'r1': None,
            'a1': None
        }
        runner_param_info = {'r1': {}}
        action_param_info = {'a1': {}}
        action_context = {'api_user': None}
        r_runner_params, r_action_params = param_utils.get_finalized_params(
            runner_param_info, action_param_info, params, action_context)
        self.assertEqual(r_runner_params, {'r1': None})
        self.assertEqual(r_action_params, {'a1': None})

    def test_get_finalized_params_no_cast(self):
        params = {
            'r1': '{{r2}}',
            'r2': 1,
            'a1': True,
            'a2': '{{r1}} {{a1}}',
            'a3': '{{action_context.api_user}}'
        }
        runner_param_info = {'r1': {}, 'r2': {}}
        action_param_info = {'a1': {}, 'a2': {}, 'a3': {}}
        action_context = {'api_user': 'noob'}
        r_runner_params, r_action_params = param_utils.get_finalized_params(
            runner_param_info, action_param_info, params, action_context)
        self.assertEqual(r_runner_params, {'r1': u'1', 'r2': 1})
        self.assertEqual(r_action_params, {'a1': True, 'a2': u'1 True', 'a3': 'noob'})

    def test_get_finalized_params_with_cast(self):
        # Note : In this test runner_params.r1 has a string value. However per runner_param_info the
        # type is an integer. The expected type is considered and cast is performed accordingly.
        params = {
            'r1': '{{r2}}',
            'r2': 1,
            'a1': True,
            'a2': '{{a1}}',
            'a3': '{{action_context.api_user}}'
        }
        runner_param_info = {'r1': {'type': 'integer'}, 'r2': {'type': 'integer'}}
        action_param_info = {'a1': {'type': 'boolean'}, 'a2': {'type': 'boolean'}, 'a3': {}}
        action_context = {'api_user': 'noob'}
        r_runner_params, r_action_params = param_utils.get_finalized_params(
            runner_param_info, action_param_info, params, action_context)
        self.assertEqual(r_runner_params, {'r1': 1, 'r2': 1})
        self.assertEqual(r_action_params, {'a1': True, 'a2': True, 'a3': 'noob'})

    def test_get_finalized_params_with_cast_overriden(self):
        params = {
            'r1': '{{r2}}',
            'r2': 1,
            'a1': '{{r1}}',
            'a2': '{{r1}}',
            'a3': '{{r1}}'
        }
        runner_param_info = {'r1': {'type': 'integer'}, 'r2': {'type': 'integer'}}
        action_param_info = {'a1': {'type': 'boolean'}, 'a2': {'type': 'string'},
                             'a3': {'type': 'integer'}, 'r1': {'type': 'string'}}
        action_context = {'api_user': 'noob'}
        r_runner_params, r_action_params = param_utils.get_finalized_params(
            runner_param_info, action_param_info, params, action_context)
        self.assertEqual(r_runner_params, {'r1': 1, 'r2': 1})
        self.assertEqual(r_action_params, {'a1': 1, 'a2': u'1', 'a3': 1})

    def test_get_finalized_params_cross_talk_no_cast(self):
        params = {
            'r1': '{{a1}}',
            'r2': 1,
            'a1': True,
            'a2': '{{r1}} {{a1}}',
            'a3': '{{action_context.api_user}}'
        }
        runner_param_info = {'r1': {}, 'r2': {}}
        action_param_info = {'a1': {}, 'a2': {}, 'a3': {}}
        action_context = {'api_user': 'noob'}
        r_runner_params, r_action_params = param_utils.get_finalized_params(
            runner_param_info, action_param_info, params, action_context)
        self.assertEqual(r_runner_params, {'r1': u'True', 'r2': 1})
        self.assertEqual(r_action_params, {'a1': True, 'a2': u'True True', 'a3': 'noob'})

    def test_get_finalized_params_cross_talk_with_cast(self):
        params = {
            'r1': '{{a1}}',
            'r2': 1,
            'r3': 1,
            'a1': True,
            'a2': '{{r1}},{{a1}},{{a3}},{{r3}}',
            'a3': '{{a1}}'
        }
        runner_param_info = {'r1': {'type': 'boolean'}, 'r2': {'type': 'integer'}, 'r3': {}}
        action_param_info = {'a1': {'type': 'boolean'}, 'a2': {'type': 'array'}, 'a3': {}}
        action_context = {}
        r_runner_params, r_action_params = param_utils.get_finalized_params(
            runner_param_info, action_param_info, params, action_context)
        self.assertEqual(r_runner_params, {'r1': True, 'r2': 1, 'r3': 1})
        self.assertEqual(r_action_params, {'a1': True, 'a2': (True, True, True, 1), 'a3': u'True'})

    def test_get_finalized_params_order(self):
        params = {
            'r1': 'p1',
            'r2': 'p2',
            'r3': 'p3',
            'a1': 'p4',
            'a2': 'p5'
        }
        runner_param_info = {'r1': {}, 'r2': {'default': 'r2'}, 'r3': {'default': 'r3'}}
        action_param_info = {'a1': {}, 'a2': {'default': 'a2'}, 'r3': {'default': 'a3'}}
        action_context = {'api_user': 'noob'}
        r_runner_params, r_action_params = param_utils.get_finalized_params(
            runner_param_info, action_param_info, params, action_context)
        self.assertEqual(r_runner_params, {'r1': u'p1', 'r2': u'p2', 'r3': u'p3'})
        self.assertEqual(r_action_params, {'a1': u'p4', 'a2': u'p5'})

        params = {}
        runner_param_info = {'r1': {}, 'r2': {'default': 'r2'}, 'r3': {'default': 'r3'}}
        action_param_info = {'a1': {}, 'a2': {'default': 'a2'}, 'r3': {'default': 'a3'}}
        action_context = {'api_user': 'noob'}
        r_runner_params, r_action_params = param_utils.get_finalized_params(
            runner_param_info, action_param_info, params, action_context)
        self.assertEqual(r_runner_params, {'r1': None, 'r2': u'r2', 'r3': u'a3'})
        self.assertEqual(r_action_params, {'a1': None, 'a2': u'a2'})

        params = {}
        runner_param_info = {'r1': {}, 'r2': {'default': 'r2'}, 'r3': {}}
        action_param_info = {'r1': {}, 'r2': {}, 'r3': {'default': 'a3'}}
        action_context = {'api_user': 'noob'}
        r_runner_params, r_action_params = param_utils.get_finalized_params(
            runner_param_info, action_param_info, params, action_context)
        self.assertEqual(r_runner_params, {'r1': None, 'r2': u'r2', 'r3': u'a3'})

    def test_get_finalized_params_non_existent_template_key_in_action_context(self):
        params = {
            'r1': 'foo',
            'r2': 2,
            'a1': 'i love tests',
            'a2': '{{action_context.lorem_ipsum}}'
        }
        runner_param_info = {'r1': {'type': 'string'}, 'r2': {'type': 'integer'}}
        action_param_info = {'a1': {'type': 'string'}, 'a2': {'type': 'string'}}
        action_context = {'api_user': 'noob', 'source_channel': 'reddit'}
        try:
            r_runner_params, r_action_params = param_utils.get_finalized_params(
                runner_param_info, action_param_info, params, action_context)
            self.fail('This should have thrown because we are trying to deref a key in ' +
                      'action context that ain\'t exist.')
        except ParamException as e:
            error_msg = 'Failed to render parameter "a2": \'dict object\' ' + \
                        'has no attribute \'lorem_ipsum\''
            self.assertTrue(error_msg in e.message)
            pass

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

    def test_get_finalized_params_with_casting_unicode_values(self):
        params = {'a1': 'unicode1 ٩(̾●̮̮̃̾•̃̾)۶ unicode2'}

        runner_param_info = {}
        action_param_info = {'a1': {'type': 'string'}}

        action_context = {}

        r_runner_params, r_action_params = param_utils.get_finalized_params(
            runner_param_info, action_param_info, params, action_context)

        expected_action_params = {
            'a1': (u'unicode1 \xd9\xa9(\xcc\xbe\xe2\x97\x8f\xcc\xae\xcc\xae\xcc'
                   u'\x83\xcc\xbe\xe2\x80\xa2\xcc\x83\xcc\xbe)\xdb\xb6 unicode2')
        }
        self.assertEqual(r_runner_params, {})
        self.assertEqual(r_action_params, expected_action_params)

    def test_get_finalized_params_with_dict(self):
        # Note : In this test runner_params.r1 has a string value. However per runner_param_info the
        # type is an integer. The expected type is considered and cast is performed accordingly.
        params = {
            'r1': '{{r2}}',
            'r2': {'r2.1': 1},
            'a1': True,
            'a2': '{{a1}}'
        }
        runner_param_info = {'r1': {'type': 'object'}, 'r2': {'type': 'object'}}
        action_param_info = {'a1': {'type': 'boolean'}, 'a2': {'type': 'boolean'}}
        r_runner_params, r_action_params = param_utils.get_finalized_params(
            runner_param_info, action_param_info, params, {})
        self.assertEqual(r_runner_params, {'r1': {'r2.1': 1}, 'r2': {'r2.1': 1}})
        self.assertEqual(r_action_params, {'a1': True, 'a2': True})

    def test_get_finalized_params_with_list(self):
        # Note : In this test runner_params.r1 has a string value. However per runner_param_info the
        # type is an integer. The expected type is considered and cast is performed accordingly.
        params = {
            'r1': '{{r2}}',
            'r2': ['1', '2'],
            'a1': True,
            'a2': 'Test',
            'a3': 'Test2',
            'a4': '{{a1}}',
            'a5': ['{{a2}}', '{{a3}}']
        }
        runner_param_info = {'r1': {'type': 'array'}, 'r2': {'type': 'array'}}
        action_param_info = {
            'a1': {'type': 'boolean'},
            'a2': {'type': 'string'},
            'a3': {'type': 'string'},
            'a4': {'type': 'boolean'},
            'a5': {'type': 'array'}
        }
        r_runner_params, r_action_params = param_utils.get_finalized_params(
            runner_param_info, action_param_info, params, {})
        self.assertEqual(r_runner_params, {'r1': ['1', '2'], 'r2': ['1', '2']})
        self.assertEqual(
            r_action_params,
            {
                'a1': True,
                'a2': 'Test',
                'a3': 'Test2',
                'a4': True,
                'a5': ['Test', 'Test2']
            }
        )

    def test_get_finalized_params_with_cyclic_dependency(self):
        params = {'r1': '{{r2}}', 'r2': '{{r1}}'}
        runner_param_info = {'r1': {}, 'r2': {}}
        action_param_info = {}
        test_pass = True
        try:
            param_utils.get_finalized_params(runner_param_info, action_param_info, params, {})
            test_pass = False
        except ParamException as e:
            test_pass = e.message.find('Cyclic') == 0
        self.assertTrue(test_pass)

    def test_get_finalized_params_with_missing_dependency(self):
        params = {'r1': '{{r3}}', 'r2': '{{r3}}'}
        runner_param_info = {'r1': {}, 'r2': {}}
        action_param_info = {}
        test_pass = True
        try:
            param_utils.get_finalized_params(runner_param_info, action_param_info, params, {})
            test_pass = False
        except ParamException as e:
            test_pass = e.message.find('Dependecy') == 0
        self.assertTrue(test_pass)

        params = {}
        runner_param_info = {'r1': {'default': '{{r3}}'}, 'r2': {'default': '{{r3}}'}}
        action_param_info = {}
        test_pass = True
        try:
            param_utils.get_finalized_params(runner_param_info, action_param_info, params, {})
            test_pass = False
        except ParamException as e:
            test_pass = e.message.find('Dependecy') == 0
        self.assertTrue(test_pass)

    def test_get_finalized_params_no_double_rendering(self):
        params = {
            'r1': '{{ action_context.h1 }}{{ action_context.h2 }}'
        }
        runner_param_info = {'r1': {}}
        action_param_info = {}
        action_context = {
            'h1': '{',
            'h2': '{ missing }}'
        }
        r_runner_params, r_action_params = param_utils.get_finalized_params(
            runner_param_info, action_param_info, params, action_context)
        self.assertEqual(r_runner_params, {'r1': '{{ missing }}'})
        self.assertEqual(r_action_params, {})

    def test_get_finalized_params_jinja_filters(self):
        params = {'cmd': 'echo {{"1.6.0" | version_bump_minor}}'}
        runner_param_info = {'r1': {}}
        action_param_info = {'cmd': {}}
        action_context = {}

        r_runner_params, r_action_params = param_utils.get_finalized_params(
            runner_param_info, action_param_info, params, action_context)

        self.assertEqual(r_action_params['cmd'], "echo 1.7.0")

    def test_get_finalized_params_param_rendering_failure(self):
        params = {'cmd': '{{a2.foo}}', 'a2': 'test'}
        action_param_info = {'cmd': {}, 'a2': {}}

        expected_msg = 'Failed to render parameter "cmd": .*'
        self.assertRaisesRegexp(ParamException,
                                expected_msg,
                                param_utils.get_finalized_params,
                                runnertype_parameter_info={},
                                action_parameter_info=action_param_info,
                                liveaction_parameters=params,
                                action_context={})

    def test_cast_param_referenced_action_doesnt_exist(self):
        # Make sure the function throws if the action doesnt exist
        expected_msg = 'Action with ref "foo.doesntexist" doesn\'t exist'
        self.assertRaisesRegexp(ValueError, expected_msg, action_param_utils.cast_params,
                                action_ref='foo.doesntexist', params={})

    def _get_liveaction_model(self, params):
        status = 'initializing'
        start_timestamp = date_utils.get_datetime_utc_now()
        action_ref = ResourceReference(name=ParamsUtilsTest.action_db.name,
                                       pack=ParamsUtilsTest.action_db.pack).ref
        liveaction_db = LiveActionDB(status=status, start_timestamp=start_timestamp,
                                     action=action_ref, parameters=params)
        liveaction_db.context = {'source_channel': 'awesome', 'api_user': 'noob'}

        return liveaction_db
