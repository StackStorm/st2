import copy
import datetime
import mock

import st2actions.utils.param_utils as param_utils
from st2common.exceptions import actionrunner
from st2common.models.db.action import ActionDB, ActionExecutionDB
from st2common.models.api.action import RunnerTypeAPI
from st2common.transport.publishers import PoolPublisher
from unittest2 import TestCase


@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
class ParamsUtilsTest(TestCase):
    action_db = None
    runnertype_db = None

    @classmethod
    def setUpClass(cls):
        super(ParamsUtilsTest, cls).setUpClass()
        ParamsUtilsTest._setup_test_models()

    def test_merge_action_runner_params_meta(self):
        required, optional, immutable = param_utils.get_params_view(
            action_db=ParamsUtilsTest.action_db,
            runner_db=ParamsUtilsTest.runnertype_db)
        merged = {}
        merged.update(required)
        merged.update(optional)
        merged.update(immutable)

        consolidated = param_utils.get_params_view(
            action_db=ParamsUtilsTest.action_db,
            runner_db=ParamsUtilsTest.runnertype_db,
            merged_only=True)

        # Validate that merged_only view works.
        self.assertEqual(merged, consolidated)

        # Validate required params.
        self.assertEqual(len(required), 1, 'Required should contain only one param.')
        self.assertTrue('actionstr' in required, 'actionstr param is a required param.')
        self.assertTrue('actionstr' not in optional and 'actionstr' not in immutable and
                        'actionstr' in merged)

        # Validate immutable params.
        self.assertTrue('runnerimmutable' in immutable, 'runnerimmutable should be in immutable.')
        self.assertTrue('actionimmutable' in immutable, 'actionimmutable should be in immutable.')

        # Validate optional params.
        for opt in optional:
            self.assertTrue(opt not in required and opt not in immutable and opt in merged,
                            'Optional parameter %s failed validation.' % opt)

    def test_merge_param_meta_values(self):

        runner_meta = copy.deepcopy(ParamsUtilsTest.runnertype_db.runner_parameters['runnerdummy'])
        action_meta = copy.deepcopy(ParamsUtilsTest.action_db.parameters['runnerdummy'])
        merged_meta = param_utils._merge_param_meta_values(action_meta=action_meta,
                                                           runner_meta=runner_meta)

        # Description is in runner meta but not in action meta.
        self.assertEqual(merged_meta['description'], runner_meta['description'])
        # Default value is overridden in action.
        self.assertEqual(merged_meta['default'], action_meta['default'])
        # Immutability is set in action.
        self.assertEqual(merged_meta['immutable'], action_meta['immutable'])

    def test_get_resolved_params(self):
        params = {
            'actionstr': 'foo',
            'some_key_that_aint_exist_in_action_or_runner': 'bar',
            'runnerint': 555,
            'runnerimmutable': 'failed_override',
            'actionimmutable': 'failed_override'
        }
        actionexec_db = self._get_action_exec_db_model(params)

        runner_params, action_params = param_utils.get_resolved_params(
            ParamsUtilsTest.runnertype_db.runner_parameters,
            ParamsUtilsTest.action_db.parameters,
            actionexec_db.parameters)

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

    def test_get_finalized_params(self):
        params = {
            'actionstr': 'foo',
            'some_key_that_aint_exist_in_action_or_runner': 'bar',
            'runnerint': 555,
            'runnerimmutable': 'failed_override',
            'actionimmutable': 'failed_override'
        }
        actionexec_db = self._get_action_exec_db_model(params)

        runner_params, action_params = param_utils.get_finalized_params(
            ParamsUtilsTest.runnertype_db.runner_parameters,
            ParamsUtilsTest.action_db.parameters,
            actionexec_db.parameters)

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

    def test_get_resolved_params_action_immutable(self):
        params = {
            'actionstr': 'foo',
            'some_key_that_aint_exist_in_action_or_runner': 'bar',
            'runnerint': 555,
            'actionimmutable': 'failed_override'
        }
        actionexec_db = self._get_action_exec_db_model(params)

        runner_params, action_params = param_utils.get_resolved_params(
            ParamsUtilsTest.runnertype_db.runner_parameters,
            ParamsUtilsTest.action_db.parameters,
            actionexec_db.parameters)

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

    def _get_action_exec_db_model(self, params):
        actionexec_db = ActionExecutionDB()
        actionexec_db.status = 'initializing'
        actionexec_db.start_timestamp = datetime.datetime.now()
        actionexec_db.action = {'name': ParamsUtilsTest.action_db.name}
        actionexec_db.parameters = params
        return actionexec_db

    @classmethod
    def _setup_test_models(cls):
        ParamsUtilsTest._setup_runner_models()
        ParamsUtilsTest._setup_action_models()

    @classmethod
    def _setup_runner_models(cls):
        test_runner = {
            'name': 'test-runner',
            'description': 'A test runner.',
            'enabled': True,
            'runner_parameters': {
                'runnerstr': {
                    'description': 'Foo str param.',
                    'type': 'string',
                    'default': 'defaultfoo'
                },
                'runnerint': {
                    'description': 'Foo int param.',
                    'type': 'number'
                },
                'runnerdummy': {
                    'description': 'Dummy param.',
                    'type': 'string',
                    'default': 'runnerdummy'
                },
                'runnerimmutable': {
                    'description': 'Immutable param.',
                    'type': 'string',
                    'default': 'runnerimmutable',
                    'immutable': True
                }
            },
            'runner_module': 'tests.test_runner'
        }
        runnertype_api = RunnerTypeAPI(**test_runner)
        ParamsUtilsTest.runnertype_db = RunnerTypeAPI.to_model(runnertype_api)

    @classmethod
    def _setup_action_models(cls):
        action_db = ActionDB()
        action_db.name = 'action-1'
        action_db.description = 'awesomeness'
        action_db.enabled = True
        action_db.content_pack = 'wolfpack'
        action_db.entry_point = ''
        action_db.runner_type = {'name': 'test-runner'}
        action_db.parameters = {
            'actionstr': {'type': 'string'},
            'actionint': {'type': 'number', 'default': 10},
            'runnerdummy': {'type': 'string', 'default': 'actiondummy', 'immutable': True},
            'runnerimmutable': {'type': 'string', 'default': 'failed_override'},
            'actionimmutable': {'type': 'string', 'default': 'actionimmutable', 'immutable': True}
        }
        action_db.required_parameters = ['actionstr']
        ParamsUtilsTest.action_db = action_db
