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

import copy
try:
    import simplejson as json
except ImportError:
    import json

import mock
import unittest2

from st2common.persistence.action import Action
import st2common.validators.api.action as action_validator
from st2common.constants.pack import SYSTEM_PACK_NAME

from tests import FunctionalTest

# ACTION_1: Good action definition.
ACTION_1 = {
    'name': 'st2.dummy.action1',
    'description': 'test description',
    'enabled': True,
    'pack': 'wolfpack',
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
    'pack': 'wolfpack',
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
    'pack': 'wolfpack',
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
    'pack': 'wolfpack',
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
    'pack': 'wolfpack',
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
    'pack': 'wolfpack',
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
    'pack': 'wolfpack',
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
    'pack': 'wolfpack',
    'entry_point': '/tmp/test/action1.sh',
    'runner_type': 'run-local',
    'parameters': {
        'a': {'type': 'string', 'default': 'A1', 'dummyfield': True},  # dummyfield is invalid.
        'b': {'type': 'string', 'default': 'B1'}
    }
}

# Same name as ACTION_1. Different pack though.
ACTION_10 = {
    'name': 'st2.dummy.action1',
    'description': 'test description',
    'enabled': True,
    'pack': 'wolfpack1',
    'entry_point': '/tmp/test/action1.sh',
    'runner_type': 'run-local',
    'parameters': {
        'a': {'type': 'string', 'default': 'A1'},
        'b': {'type': 'string', 'default': 'B1'}
    }
}

# Good action with a system pack
ACTION_11 = {
    'name': 'st2.dummy.action11',
    'pack': SYSTEM_PACK_NAME,
    'description': 'test description',
    'enabled': True,
    'entry_point': '/tmp/test/action2.py',
    'runner_type': 'run-local',
    'parameters': {
        'c': {'type': 'string', 'default': 'C1', 'position': 0},
        'd': {'type': 'string', 'default': 'D1', 'immutable': True}
    }
}


class TestActionController(FunctionalTest):
    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    def test_get_one_using_id(self):
        post_resp = self.__do_post(ACTION_1)
        action_id = self.__get_action_id(post_resp)
        get_resp = self.__do_get_one(action_id)
        self.assertEqual(get_resp.status_int, 200)
        self.assertEqual(self.__get_action_id(get_resp), action_id)
        self.__do_delete(action_id)

    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    def test_get_one_using_ref(self):
        ref = '.'.join([ACTION_1['pack'], ACTION_1['name']])
        action_id = self.__get_action_id(self.__do_post(ACTION_1))
        get_resp = self.__do_get_one(ref)
        self.assertEqual(get_resp.status_int, 200)
        self.assertEqual(self.__get_action_id(get_resp), action_id)
        self.assertEqual(get_resp.json['ref'], ref)
        self.__do_delete(action_id)

    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
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

    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    def test_get_all(self):
        action_1_ref = '.'.join([ACTION_1['pack'], ACTION_1['name']])
        action_1_id = self.__get_action_id(self.__do_post(ACTION_1))
        action_2_id = self.__get_action_id(self.__do_post(ACTION_2))
        resp = self.app.get('/v1/actions')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 2, '/v1/actions did not return all actions.')

        item = [i for i in resp.json if i['id'] == action_1_id][0]
        self.assertEqual(item['ref'], action_1_ref)

        self.__do_delete(action_1_id)
        self.__do_delete(action_2_id)

    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    def test_query(self):
        action_1_id = self.__get_action_id(self.__do_post(ACTION_1))
        action_2_id = self.__get_action_id(self.__do_post(ACTION_2))
        resp = self.app.get('/v1/actions?name=%s' % ACTION_1['name'])
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 1, '/v1/actions did not return all actions.')
        self.__do_delete(action_1_id)
        self.__do_delete(action_2_id)

    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    def test_get_one_fail(self):
        resp = self.app.get('/v1/actions/1', expect_errors=True)
        self.assertEqual(resp.status_int, 404)

    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    def test_post_delete(self):
        post_resp = self.__do_post(ACTION_1)
        self.assertEqual(post_resp.status_int, 201)
        self.__do_delete(self.__get_action_id(post_resp))

    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    def test_post_action_with_bad_params(self):
        post_resp = self.__do_post(ACTION_9, expect_errors=True)
        self.assertEqual(post_resp.status_int, 400)

    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    def test_post_no_description_field(self):
        post_resp = self.__do_post(ACTION_6)
        self.assertEqual(post_resp.status_int, 201)
        self.__do_delete(self.__get_action_id(post_resp))

    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    def test_post_no_enable_field(self):
        post_resp = self.__do_post(ACTION_3)
        self.assertEqual(post_resp.status_int, 201)
        self.assertIn('enabled', post_resp.body)

        # If enabled field is not provided it should default to True
        data = json.loads(post_resp.body)
        self.assertDictContainsSubset({'enabled': True}, data)

        self.__do_delete(self.__get_action_id(post_resp))

    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    def test_post_false_enable_field(self):
        post_resp = self.__do_post(ACTION_4)
        self.assertEqual(post_resp.status_int, 201)

        data = json.loads(post_resp.body)
        self.assertDictContainsSubset({'enabled': False}, data)

        self.__do_delete(self.__get_action_id(post_resp))

    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    def test_post_discard_id_field(self):
        post_resp = self.__do_post(ACTION_7)
        self.assertEqual(post_resp.status_int, 201)
        self.assertIn('id', post_resp.body)
        data = json.loads(post_resp.body)
        # Verify that user-provided id is discarded.
        self.assertNotEquals(data['id'], ACTION_7['id'])
        self.__do_delete(self.__get_action_id(post_resp))

    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    def test_post_duplicate(self):
        action_ids = []

        post_resp = self.__do_post(ACTION_1)
        self.assertEqual(post_resp.status_int, 201)
        action_in_db = Action.get_by_name(ACTION_1.get('name'))
        self.assertTrue(action_in_db is not None, 'Action must be in db.')
        action_ids.append(self.__get_action_id(post_resp))

        post_resp = self.__do_post(ACTION_1, expect_errors=True)
        # Verify name conflict
        self.assertEqual(post_resp.status_int, 409)

        post_resp = self.__do_post(ACTION_10)
        action_ids.append(self.__get_action_id(post_resp))
        # Verify action with same name but different pack is written.
        self.assertEqual(post_resp.status_int, 201)

        for i in action_ids:
            self.__do_delete(i)

    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    def test_post_put_delete(self):
        action = copy.copy(ACTION_1)
        post_resp = self.__do_post(action)
        self.assertEqual(post_resp.status_int, 201)
        self.assertIn('id', post_resp.body)
        body = json.loads(post_resp.body)
        action['id'] = body['id']
        action['description'] = 'some other test description'
        pack = action['pack']
        del action['pack']
        self.assertNotIn('pack', action)
        put_resp = self.__do_put(action['id'], action)
        self.assertEqual(put_resp.status_int, 200)
        self.assertIn('description', put_resp.body)
        body = json.loads(put_resp.body)
        self.assertEqual(body['description'], action['description'])
        self.assertEqual(body['pack'], pack)
        self.__do_delete(self.__get_action_id(post_resp))

    def test_post_invalid_runner_type(self):
        post_resp = self.__do_post(ACTION_5, expect_errors=True)
        self.assertEqual(post_resp.status_int, 400)

    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    def test_delete(self):
        post_resp = self.__do_post(ACTION_1)
        del_resp = self.__do_delete(self.__get_action_id(post_resp))
        self.assertEqual(del_resp.status_int, 204)

    # TODO: Re-enable those tests after we ensure DB is flushed in setUp
    # and each test starts in a clean state

    @unittest2.skip('Skip because of test polution')
    def test_update_action_belonging_to_system_pack(self):
        post_resp = self.__do_post(ACTION_11)
        action_id = self.__get_action_id(post_resp)
        put_resp = self.__do_put(action_id, ACTION_11, expect_errors=True)
        self.assertEqual(put_resp.status_int, 400)

    @unittest2.skip('Skip because of test polution')
    def test_delete_action_belonging_to_system_pack(self):
        post_resp = self.__do_post(ACTION_11)
        action_id = self.__get_action_id(post_resp)
        del_resp = self.__do_delete(action_id, expect_errors=True)
        self.assertEqual(del_resp.status_int, 400)

    @staticmethod
    def __get_action_id(resp):
        return resp.json['id']

    @staticmethod
    def __get_action_name(resp):
        return resp.json['name']

    def __do_get_one(self, action_id, expect_errors=False):
        return self.app.get('/v1/actions/%s' % action_id, expect_errors=expect_errors)

    def __do_post(self, action, expect_errors=False):
        return self.app.post_json('/v1/actions', action, expect_errors=expect_errors)

    def __do_put(self, action_id, action, expect_errors=False):
        return self.app.put_json('/v1/actions/%s' % action_id, action, expect_errors=expect_errors)

    def __do_delete(self, action_id, expect_errors=False):
        return self.app.delete('/v1/actions/%s' % action_id, expect_errors=expect_errors)
