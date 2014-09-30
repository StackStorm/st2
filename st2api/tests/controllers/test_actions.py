import copy
try:
    import simplejson as json
except ImportError:
    import json

import mock

from st2api.controllers.actions import ActionsController
from st2common.persistence.action import Action
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

# ACTION_3: No enabled field
ACTION_3 = {
    'name': 'st2.dummy.action3',
    'description': 'test description',
    'content_pack': 'wolfpack',
    'entry_point': '/tmp/test/action1.sh',
    'runner_type': 'run-local',
    'parameters': {
        'a': {'type': 'string', 'default': 'A1'},
        'b': {'type': 'string', 'default': 'B1'}
    }
}

# ACTION_4: Enabled field is False
ACTION_4 = {
    'name': 'st2.dummy.action4',
    'description': 'test description',
    'enabled': False,
    'content_pack': 'wolfpack',
    'entry_point': '/tmp/test/action1.sh',
    'runner_type': 'run-local',
    'parameters': {
        'a': {'type': 'string', 'default': 'A1'},
        'b': {'type': 'string', 'default': 'B1'}
    }
}

# ACTION_5: Invalid runner_type
ACTION_5 = {
    'name': 'st2.dummy.action5',
    'description': 'test description',
    'enabled': False,
    'content_pack': 'wolfpack',
    'entry_point': '/tmp/test/action1.sh',
    'runner_type': 'xyzxyz',
    'parameters': {
        'a': {'type': 'string', 'default': 'A1'},
        'b': {'type': 'string', 'default': 'B1'}
    }
}

# ACTION_6: No description field.
ACTION_6 = {
    'name': 'st2.dummy.action6',
    'enabled': False,
    'content_pack': 'wolfpack',
    'entry_point': '/tmp/test/action1.sh',
    'runner_type': 'run-local',
    'parameters': {
        'a': {'type': 'string', 'default': 'A1'},
        'b': {'type': 'string', 'default': 'B1'}
    }
}

# ACTION_7: id field provided
ACTION_7 = {
    'id': 'foobar',
    'name': 'st2.dummy.action7',
    'description': 'test description',
    'enabled': False,
    'content_pack': 'wolfpack',
    'entry_point': '/tmp/test/action1.sh',
    'runner_type': 'run-local',
    'parameters': {
        'a': {'type': 'string', 'default': 'A1'},
        'b': {'type': 'string', 'default': 'B1'}
    }
}

# ACTION_8: id field provided
ACTION_8 = {
    'name': 'st2.dummy.action8',
    'description': 'test description',
    'enabled': True,
    'content_pack': 'wolfpack',
    'entry_point': '/tmp/test/action1.sh',
    'runner_type': 'run-local',
    'parameters': {
        'cmd': {'type': 'string', 'default': 'A1'},
        'b': {'type': 'string', 'default': 'B1'}
    }
}

# ACTION_9: Parameter dict has fields not part of JSONSchema spec.
ACTION_9 = {
    'name': 'st2.dummy.action9',
    'description': 'test description',
    'enabled': True,
    'content_pack': 'wolfpack',
    'entry_point': '/tmp/test/action1.sh',
    'runner_type': 'run-local',
    'parameters': {
        'a': {'type': 'string', 'default': 'A1', 'dummyfield': True},  # dummyfield is invalid.
        'b': {'type': 'string', 'default': 'B1'}
    }
}


class TestActionController(FunctionalTest):
    @mock.patch.object(ActionsController, '_is_valid_content_pack', mock.MagicMock(
        return_value=True))
    def test_get_one(self):
        post_resp = self.__do_post(ACTION_1)
        action_id = self.__get_action_id(post_resp)
        get_resp = self.__do_get_one(action_id)
        self.assertEqual(get_resp.status_int, 200)
        self.assertEqual(self.__get_action_id(get_resp), action_id)
        self.__do_delete(action_id)

    @mock.patch.object(ActionsController, '_is_valid_content_pack', mock.MagicMock(
        return_value=True))
    def test_get_one_validate_params(self):
        post_resp = self.__do_post(ACTION_1)
        action_id = self.__get_action_id(post_resp)
        get_resp = self.__do_get_one(action_id)
        self.assertEqual(get_resp.status_int, 200)
        self.assertEqual(self.__get_action_id(get_resp), action_id)
        expected_args = ACTION_1['parameters']
        self.assertEqual(get_resp.json['parameters'], expected_args)
        self.__do_delete(action_id)

    @mock.patch.object(ActionsController, '_is_valid_content_pack', mock.MagicMock(
        return_value=True))
    def test_get_all(self):
        action_1_id = self.__get_action_id(self.__do_post(ACTION_1))
        action_2_id = self.__get_action_id(self.__do_post(ACTION_2))
        resp = self.app.get('/actions')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 2, '/actions did not return all actions.')
        self.__do_delete(action_1_id)
        self.__do_delete(action_2_id)

    @mock.patch.object(ActionsController, '_is_valid_content_pack', mock.MagicMock(
        return_value=True))
    def test_get_one_fail(self):
        resp = self.app.get('/actions/1', expect_errors=True)
        self.assertEqual(resp.status_int, 404)

    @mock.patch.object(ActionsController, '_is_valid_content_pack', mock.MagicMock(
        return_value=True))
    def test_post_delete(self):
        post_resp = self.__do_post(ACTION_1)
        self.assertEqual(post_resp.status_int, 201)
        self.__do_delete(self.__get_action_id(post_resp))

    @mock.patch.object(ActionsController, '_is_valid_content_pack', mock.MagicMock(
        return_value=True))
    def test_post_action_with_bad_params(self):
        post_resp = self.__do_post(ACTION_9, expect_errors=True)
        self.assertEqual(post_resp.status_int, 400)

    @mock.patch.object(ActionsController, '_is_valid_content_pack', mock.MagicMock(
        return_value=True))
    def test_post_no_description_field(self):
        post_resp = self.__do_post(ACTION_6)
        self.assertEqual(post_resp.status_int, 201)
        self.__do_delete(self.__get_action_id(post_resp))

    @mock.patch.object(ActionsController, '_is_valid_content_pack', mock.MagicMock(
        return_value=True))
    def test_post_no_enable_field(self):
        post_resp = self.__do_post(ACTION_3)
        self.assertEqual(post_resp.status_int, 201)
        self.assertIn('enabled', post_resp.body)

        # If enabled field is not provided it should default to True
        data = json.loads(post_resp.body)
        self.assertDictContainsSubset({'enabled': True}, data)

        self.__do_delete(self.__get_action_id(post_resp))

    @mock.patch.object(ActionsController, '_is_valid_content_pack', mock.MagicMock(
        return_value=True))
    def test_post_false_enable_field(self):
        post_resp = self.__do_post(ACTION_4)
        self.assertEqual(post_resp.status_int, 201)

        data = json.loads(post_resp.body)
        self.assertDictContainsSubset({'enabled': False}, data)

        self.__do_delete(self.__get_action_id(post_resp))

    @mock.patch.object(ActionsController, '_is_valid_content_pack', mock.MagicMock(
        return_value=True))
    def test_post_discard_id_field(self):
        post_resp = self.__do_post(ACTION_7)
        self.assertEqual(post_resp.status_int, 201)
        self.assertIn('id', post_resp.body)
        data = json.loads(post_resp.body)
        # Verify that user-provided id is discarded.
        self.assertNotEquals(data['id'], ACTION_7['id'])
        self.__do_delete(self.__get_action_id(post_resp))

    @mock.patch.object(ActionsController, '_is_valid_content_pack', mock.MagicMock(
        return_value=True))
    def test_post_name_duplicate(self):
        action_ids = []

        post_resp = self.__do_post(ACTION_1)
        self.assertEqual(post_resp.status_int, 201)
        action_in_db = Action.get_by_name(ACTION_1.get('name'))
        self.assertTrue(action_in_db is not None, 'Action must be in db.')
        action_ids.append(self.__get_action_id(post_resp))

        post_resp = self.__do_post(ACTION_1, expect_errors=True)
        # Verify name conflict
        self.assertEqual(post_resp.status_int, 409)

        for i in action_ids:
            self.__do_delete(i)

    @mock.patch.object(ActionsController, '_is_valid_content_pack', mock.MagicMock(
        return_value=True))
    def test_post_put_delete(self):
        action = copy.copy(ACTION_1)
        post_resp = self.__do_post(action)
        self.assertEqual(post_resp.status_int, 201)
        self.assertIn('id', post_resp.body)
        body = json.loads(post_resp.body)
        action['id'] = body['id']
        action['description'] = 'some other test description'
        put_resp = self.__do_put(action['id'], action)
        self.assertEqual(put_resp.status_int, 200)
        self.assertIn('description', put_resp.body)
        body = json.loads(put_resp.body)
        self.assertEqual(body['description'], action['description'])
        self.__do_delete(self.__get_action_id(post_resp))

    @mock.patch.object(ActionsController, '_is_valid_content_pack', mock.MagicMock(
        return_value=True))
    def test_post_invalid_runner_type(self):
        post_resp = self.__do_post(ACTION_5, expect_errors=True)
        self.assertEqual(post_resp.status_int, 404)

    @mock.patch.object(ActionsController, '_is_valid_content_pack', mock.MagicMock(
        return_value=True))
    def test_delete(self):
        post_resp = self.__do_post(ACTION_1)
        del_resp = self.__do_delete(self.__get_action_id(post_resp))
        self.assertEqual(del_resp.status_int, 204)

    @staticmethod
    def __get_action_id(resp):
        return resp.json['id']

    @staticmethod
    def __get_action_name(resp):
        return resp.json['name']

    def __do_get_one(self, action_id, expect_errors=False):
        return self.app.get('/actions/%s' % action_id, expect_errors=expect_errors)

    def __do_post(self, action, expect_errors=False):
        return self.app.post_json('/actions', action, expect_errors=expect_errors)

    def __do_put(self, action_id, action, expect_errors=False):
        return self.app.put_json('/actions/%s' % action_id, action, expect_errors=expect_errors)

    def __do_delete(self, action_id, expect_errors=False):
        return self.app.delete('/actions/%s' % action_id, expect_errors=expect_errors)
