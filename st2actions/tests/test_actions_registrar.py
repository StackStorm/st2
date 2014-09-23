try:
    import simplejson as json
except ImportError:
    import json
import os

import mock

import st2actions.bootstrap.actionsregistrar as actions_registrar
from st2common.persistence.action import Action
from st2common.models.db.action import RunnerTypeDB
from st2tests.base import DbTestCase

MOCK_RUNNER_TYPE_DB = RunnerTypeDB()
MOCK_RUNNER_TYPE_DB.name = 'run-local'
MOCK_RUNNER_TYPE_DB.runner_module = 'st2.runners.local'


class ActionsRegistrarTest(DbTestCase):
    @mock.patch.object(actions_registrar.ActionsRegistrar, '_has_valid_runner_type',
                       mock.MagicMock(return_value=(True, MOCK_RUNNER_TYPE_DB)))
    def test_register_all_actions(self):
        try:
            content_packs_base_path = os.path.join(
                os.path.dirname(os.path.realpath(__file__)), 'fixtures/packs/')
            all_actions_in_db = Action.get_all()
            actions_registrar.register_actions(content_packs_base_path=content_packs_base_path)
            all_actions_in_db = Action.get_all()
            self.assertTrue(len(all_actions_in_db) > 0)
        except Exception as e:
            print(str(e))
            self.fail('All actions must be registered without exceptions.')

    def test_register_actions_from_bad_pack(self):
        content_packs_base_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 'fixtures/badpacks/')
        try:
            actions_registrar.register_actions(content_packs_base_path=content_packs_base_path)
            self.fail('Should have thrown.')
        except:
            pass

    @mock.patch.object(actions_registrar.ActionsRegistrar, '_has_valid_runner_type',
                       mock.MagicMock(return_value=(True, MOCK_RUNNER_TYPE_DB)))
    def test_content_pack_name_missing(self):
        registrar = actions_registrar.ActionsRegistrar()
        action_file = os.path.join(os.path.dirname(
            os.path.realpath(__file__)),
            'fixtures/packs/wolfpack/actions/action_3_content_pack_missing.json')
        registrar._register_action('dummy', action_file)
        action_name = None
        with open(action_file, 'r') as fd:
            content = json.load(fd)
            action_name = str(content['name'])
            action_db = Action.get_by_name(action_name)
            self.assertEqual(action_db.content_pack, 'dummy', 'Content pack must be ' +
                             'set to dummy')
            Action.delete(action_db)
