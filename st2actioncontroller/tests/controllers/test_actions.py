from tests import FunctionalTest
import json
# ACTION_1: Good action definition.
ACTION_1 = {
    'name': 'st2.dummy.action1',
    'description': 'test description',
    'enabled': True,
    'artifact_path': '/tmp/test',
    'entry_point': 'action1.sh',
    'runner_type': 'shell',
    'parameter_names': ['a', 'b']
}
# ACTION_2: Good action definition.
ACTION_2 = {
    'name': 'st2.dummy.action2',
    'description': 'test description',
    'enabled': True,
    'artifact_path': '/tmp/test',
    'entry_point': 'action2.py',
    'runner_type': 'python',
    'parameter_names': ['c', 'd']
}
# ACTION_3: No enabled field
ACTION_3 = {
    'name': 'st2.dummy.action3',
    'description': 'test description',
    'artifact_path': '/tmp/test',
    'entry_point': 'action1.sh',
    'runner_type': 'shell',
    'parameter_names': ['a', 'b']
}
# ACTION_4: Enabled field is False
ACTION_4 = {
    'name': 'st2.dummy.action4',
    'description': 'test description',
    'enabled': False,
    'artifact_path': '/tmp/test',
    'entry_point': 'action1.sh',
    'runner_type': 'shell',
    'parameter_names': ['a', 'b']
}
# ACTION_5: Invalid runner_type
ACTION_5 = {
    'name': 'st2.dummy.action5',
    'description': 'test description',
    'enabled': False,
    'artifact_path': '/tmp/test',
    'entry_point': 'action1.sh',
    'runner_type': 'xyzxyz',
    'parameter_names': ['a', 'b']
}
# ACTION_6: No description field.
ACTION_6 = {
    'name': 'st2.dummy.action6',
    'enabled': False,
    'artifact_path': '/tmp/test',
    'entry_point': 'action1.sh',
    'runner_type': 'shell',
    'parameter_names': ['a', 'b']
}
# ACTION_7: id field provided
ACTION_7 = {
    'id': 'foobar',
    'name': 'st2.dummy.action7',
    'description': 'test description',
    'enabled': False,
    'artifact_path': '/tmp/test',
    'entry_point': 'action1.sh',
    'runner_type': 'shell',
    'parameter_names': ['a', 'b']
}


class TestActionController(FunctionalTest):

    def test_get_one(self):
        post_resp = self.__do_post(ACTION_1)
        action_id = self.__get_action_id(post_resp)
        get_resp = self.__do_get_one(action_id)
        self.assertEquals(get_resp.status_int, 200)
        self.assertEquals(self.__get_action_id(get_resp), action_id)
        self.__do_delete(action_id)

    def test_get_all(self):
        action_1_id = self.__get_action_id(self.__do_post(ACTION_1))
        action_2_id = self.__get_action_id(self.__do_post(ACTION_2))
        resp = self.app.get('/actions')
        self.assertEqual(resp.status_int, 200)
        self.assertEquals(len(resp.json), 2, '/actions did not return all actions.')
        self.__do_delete(action_1_id)
        self.__do_delete(action_2_id)

    def test_get_one_fail(self):
        resp = self.app.get('/actions/1', expect_errors=True)
        self.assertEqual(resp.status_int, 404)

    def test_post_delete(self):
        post_resp = self.__do_post(ACTION_1)
        self.assertEquals(post_resp.status_int, 201)
        self.__do_delete(self.__get_action_id(post_resp))

    def test_post_no_description_field(self):
        post_resp = self.__do_post(ACTION_6)
        self.assertEquals(post_resp.status_int, 201)
        self.assertIn('description', post_resp.body)
        self.__do_delete(self.__get_action_id(post_resp))

    def test_post_no_enable_field(self):
        post_resp = self.__do_post(ACTION_3)
        self.assertEquals(post_resp.status_int, 201)
        self.assertIn('enabled', post_resp.body)

        # If enabled field is not provided it should default to True
        data = json.loads(post_resp.body)
        self.assertDictContainsSubset({'enabled': True}, data)

        self.__do_delete(self.__get_action_id(post_resp))

    def test_post_false_enable_field(self):
        post_resp = self.__do_post(ACTION_4)
        self.assertEquals(post_resp.status_int, 201)

        data = json.loads(post_resp.body)
        self.assertDictContainsSubset({'enabled': False}, data)

        self.__do_delete(self.__get_action_id(post_resp))

    def test_post_discard_id_field(self):
        post_resp = self.__do_post(ACTION_7)
        self.assertEquals(post_resp.status_int, 201)
        self.assertIn('id', post_resp.body)
        data = json.loads(post_resp.body)
        # Verify that user-provided id is discarded.
        self.assertNotEquals(data['id'], ACTION_7['id'])
        self.__do_delete(self.__get_action_id(post_resp))

    def test_post_name_duplicate(self):
        post_resp = self.__do_post(ACTION_1)
        self.assertEquals(post_resp.status_int, 201)

        post_resp = self.__do_post(ACTION_1)
        # Verify name conflict
        self.assertEquals(post_resp.status_int, 409)

#    def test_post_invalid_runner_type(self):
#        post_resp = self.__do_post(ACTION_5)
#        self.assertEquals(post_resp.status_int, 403)
#        self.__do_delete(self.__get_action_id(post_resp))

    def test_delete(self):
        post_resp = self.__do_post(ACTION_1)
        del_resp = self.__do_delete(self.__get_action_id(post_resp))
        self.assertEquals(del_resp.status_int, 204)

    @staticmethod
    def __get_action_id(resp):
        return resp.json['id']

    def __do_get_one(self, action_id):
        return self.app.get('/actions/%s' % action_id, expect_errors=True)

    def __do_post(self, action):
        return self.app.post_json('/actions', action, expect_errors=True)

    def __do_delete(self, action_id):
        return self.app.delete('/actions/%s' % action_id, expect_errors=True)
