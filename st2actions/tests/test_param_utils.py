import copy
import mock

import st2actions.utils.param_utils as param_utils
from st2common.models.db.action import (ActionDB)
from st2common.models.api.action import RunnerTypeAPI
from st2common.persistence.action import (Action, RunnerType)
from st2common.transport.publishers import PoolPublisher
from st2tests.base import DbTestCase

import tests.config as tests_config
tests_config.parse_args()


@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
class ParamsUtilsTest(DbTestCase):
    action_db = None
    runnertype_db = None

    @classmethod
    def setUpClass(cls):
        super(DbTestCase, cls).setUpClass()
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

    @classmethod
    def _setup_test_models(cls):
        ParamsUtilsTest.setup_runner()
        ParamsUtilsTest.setup_action_models()

    @classmethod
    def setup_runner(cls):
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
        ParamsUtilsTest.runnertype_db = RunnerType.add_or_update(
            RunnerTypeAPI.to_model(runnertype_api))

    @classmethod
    def setup_action_models(cls):
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
            'actionimmutable': {'type': 'string', 'default': 'actionimmutable', 'immutable': True}
        }
        action_db.required_parameters = ['actionstr']
        ParamsUtilsTest.action_db = Action.add_or_update(action_db)
