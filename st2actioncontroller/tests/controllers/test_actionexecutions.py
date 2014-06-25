from nose.tools import nottest
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
ACTION_EXECUTION_1 = {
    'action': {'name': 'st2.dummy.action1'},
    'runner_parameters': {},
    'action_parameters': {}
}
ACTION_EXECUTION_2 = {
    'action': {'name': 'st2.dummy.action1'},
    'runner_parameters': {},
    'action_parameters': {}
}


@nottest
class TestActionExecutionsController(FunctionalTest):

    @classmethod
    def setUpClass(cls):
        super(TestActionExecutionsController, cls).setUpClass()
        global ACTION_1
        post_resp = cls.app.post_json('/actions', ACTION_1)
        ACTION_1['id'] = post_resp.json['id']

    @classmethod
    def tearDownClass(cls):
        cls.app.delete('/actions/%s' % ACTION_1['id'])
        super(TestActionExecutionsController, cls).tearDownClass()

    def test_get_one(self):
        post_resp = self.__do_post(ACTION_EXECUTION_1)
        actionexecution_id = self.__get_actionexecution_id(post_resp)
        get_resp = self.__do_get_one(actionexecution_id)
        self.assertEquals(get_resp.status_int, 200)
        self.assertEquals(self.__get_actionexecution_id(get_resp), actionexecution_id)
        self.__do_delete(actionexecution_id)

    def test_get_all(self):
        actionexecution_1_id = self.__get_actionexecution_id(self.__do_post(ACTION_EXECUTION_1))
        actionexecution_2_id = self.__get_actionexecution_id(self.__do_post(ACTION_EXECUTION_2))
        resp = self.app.get('/actionexecutions')
        self.assertEqual(resp.status_int, 200)
        self.assertEquals(len(resp.json), 2,
                          '/actionexecutions did not return all actionexecutions.')
        self.__do_delete(actionexecution_1_id)
        self.__do_delete(actionexecution_2_id)

    def test_get_one_fail(self):
        resp = self.app.get('/actionexecutions/1', expect_errors=True)
        self.assertEqual(resp.status_int, 404)

    def test_post_delete(self):
        post_resp = self.__do_post(ACTION_EXECUTION_1)
        self.assertEquals(post_resp.status_int, 201)
        self.__do_delete(self.__get_actionexecution_id(post_resp))

    def test_delete(self):
        post_resp = self.__do_post(ACTION_EXECUTION_1)
        del_resp = self.__do_delete(self.__get_actionexecution_id(post_resp))
        self.assertEquals(del_resp.status_int, 204)

    @staticmethod
    def __get_actionexecution_id(resp):
        return resp.json['id']

    def __do_get_one(self, actionexecution_id):
        return self.app.get('/actionexecutions/%s' % actionexecution_id)

    def __do_post(self, actionexecution):
        return self.app.post_json('/actionexecutions', actionexecution)

    def __do_delete(self, actionexecution_id):
        return self.app.delete('/actionexecutions/%s' % actionexecution_id)
