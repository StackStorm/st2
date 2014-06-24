from tests import FunctionalTest

ACTION_1 = {
    'name': 'st2.dummy.action1',
    'description': 'test description',
    'enabled': True,
    'artifact_path': '/tmp/test',
    'entry_point': 'action1.sh',
    'runner_type': 'shell',
    'parameter_names': ['a', 'b']
}
ACTION_2 = {
    'name': 'st2.dummy.action2',
    'description': 'test description',
    'enabled': True,
    'artifact_path': '/tmp/test',
    'entry_point': 'action2.py',
    'runner_type': 'python',
    'parameter_names': ['c', 'd']
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

    def test_delete(self):
        post_resp = self.__do_post(ACTION_1)
        del_resp = self.__do_delete(self.__get_action_id(post_resp))
        self.assertEquals(del_resp.status_int, 204)

    @staticmethod
    def __get_action_id(resp):
        return resp.json['id']

    def __do_get_one(self, action_id):
        return self.app.get('/actions/%s' % action_id)

    def __do_post(self, action):
        return self.app.post_json('/actions', action)

    def __do_delete(self, action_id):
        return self.app.delete('/actions/%s' % action_id)
