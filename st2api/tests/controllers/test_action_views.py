import mock

import st2common.validators.api.action as action_validator
from tests import FunctionalTest

# ACTION_1: Good action definition.
ACTION_1 = {
    'name': 'st2.dummy.action1',
    'description': 'test description',
    'enabled': True,
    'content_pack': 'wolfpack',
    'entry_point': '/tmp/test/action1.sh',
    'runner_type': 'run-local',
    'parameters': {
        'a': {'type': 'string', 'default': 'A1'},
        'b': {'type': 'string', 'default': 'B1'}
    }
}

# ACTION_2: Good action definition. No content pack.
ACTION_2 = {
    'name': 'st2.dummy.action2',
    'description': 'test description',
    'enabled': True,
    'entry_point': '/tmp/test/action2.py',
    'runner_type': 'run-local',
    'parameters': {
        'c': {'type': 'string', 'default': 'C1', 'position': 0},
        'd': {'type': 'string', 'default': 'D1', 'immutable': True}
    }
}


class TestActionViews(FunctionalTest):
    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    def test_get_one(self):
        post_resp = self._do_post(ACTION_1)
        action_id = self._get_action_id(post_resp)
        get_resp = self._do_get_one(action_id)
        self.assertEqual(get_resp.status_int, 200)
        self.assertEqual(self._get_action_id(get_resp), action_id)
        self._do_delete(action_id)

    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    def test_get_all(self):
        action_1_id = self._get_action_id(self._do_post(ACTION_1))
        action_2_id = self._get_action_id(self._do_post(ACTION_2))
        resp = self.app.get('/actions/views/overview')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 2, '/actions/views/overview did not return all actions.')
        self._do_delete(action_1_id)
        self._do_delete(action_2_id)

    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    def test_get_all_filter_by_name(self):
        action_1_id = self._get_action_id(self._do_post(ACTION_1))
        action_2_id = self._get_action_id(self._do_post(ACTION_2))
        resp = self.app.get('/actions/views/overview?name=%s' % str('st2.dummy.action2'))
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json[0]['id'], action_2_id, 'Filtering failed')
        self._do_delete(action_1_id)
        self._do_delete(action_2_id)

    @staticmethod
    def _get_action_id(resp):
        return resp.json['id']

    @staticmethod
    def _get_action_name(resp):
        return resp.json['name']

    def _do_get_one(self, action_id, expect_errors=False):
        return self.app.get('/actions/views/overview/%s' % action_id, expect_errors=expect_errors)

    def _do_post(self, action, expect_errors=False):
        return self.app.post_json('/actions', action, expect_errors=expect_errors)

    def _do_delete(self, action_id, expect_errors=False):
        return self.app.delete('/actions/%s' % action_id, expect_errors=expect_errors)


class TestParametersView(FunctionalTest):
    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    def test_get_one(self):
        post_resp = self.app.post_json('/actions', ACTION_1)
        action_id = post_resp.json['id']
        get_resp = self.app.get('/actions/views/parameters/%s' % action_id)
        self.assertEqual(get_resp.status_int, 200)
        self.assertTrue(get_resp.json['parameters']['required'] is not None, get_resp.json)
        self.assertTrue(get_resp.json['parameters']['optional'] is not None, get_resp.json)
        self.assertTrue(get_resp.json['parameters']['immutable'] is not None, get_resp.json)
        self.app.delete('/actions/%s' % action_id)
