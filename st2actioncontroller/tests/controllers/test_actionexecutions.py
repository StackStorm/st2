import copy
import mock
from nose.tools import nottest
from tests import FunctionalTest

from st2actioncontroller.controllers.actionexecutions import ActionExecutionsController

ACTION_1 = {
    'name': 'st2.dummy.action1',
    'description': 'test description',
    'enabled': True,
    'entry_point': '/tmp/test/action1.sh',
    'runner_type': 'shell',
    'parameters': {'a':'1', 'b':'2'}
}
ACTION_2 = {
    'name': 'st2.dummy.action2',
    'description': 'another test description',
    'enabled': True,
    'entry_point': '/tmp/test/action2.sh',
    'runner_type': 'shell',
    'parameters': {'c':'3', 'd':'4'}
}
ACTION_EXECUTION_1 = {
    'action': {'name': 'st2.dummy.action1'},
    'parameters': {}
}
ACTION_EXECUTION_2 = {
    'action': {'name': 'st2.dummy.action2'},
    'parameters': {}
}


class FakeResponse(object):

    def __init__(self, text, status_code, reason):
        self.text = text
        self.status_code = status_code
        self.reason = reason

    def json(self):
        return json.loads(self.text)

    def raise_for_status(self):
        raise Exception(self.reason)


class TestActionExecutionsController(FunctionalTest):

    @classmethod
    def setUpClass(cls):
        super(TestActionExecutionsController, cls).setUpClass()
        cls.action1 = copy.copy(ACTION_1)
        post_resp = cls.app.post_json('/actions', cls.action1)
        cls.action1['id'] = post_resp.json['id']
        cls.action2 = copy.copy(ACTION_2)
        post_resp = cls.app.post_json('/actions', cls.action2)
        cls.action2['id'] = post_resp.json['id']

    @classmethod
    def tearDownClass(cls):
        cls.app.delete('/actions/%s' % cls.action1['id'])
        cls.app.delete('/actions/%s' % cls.action2['id'])
        super(TestActionExecutionsController, cls).tearDownClass()

    @mock.patch.object(
        ActionExecutionsController, '_issue_liveaction_post',
        mock.MagicMock(return_value=\
            (FakeResponse('', 200, 'OK'), False)))
    @mock.patch.object(
        ActionExecutionsController, '_issue_liveaction_delete',
        mock.MagicMock(return_value=\
            (FakeResponse('', 204, 'NO CONTENT'), False)))
    def test_get_one(self):
        post_resp = self.__do_post(ACTION_EXECUTION_1)
        actionexecution_id = self.__get_actionexecution_id(post_resp)
        get_resp = self.__do_get_one(actionexecution_id)
        self.assertEquals(get_resp.status_int, 200)
        self.assertEquals(self.__get_actionexecution_id(get_resp), actionexecution_id)
        self.__do_delete(actionexecution_id)

    @mock.patch.object(
        ActionExecutionsController, '_issue_liveaction_post',
        mock.MagicMock(return_value=\
            (FakeResponse('', 200, 'OK'), False)))
    @mock.patch.object(
        ActionExecutionsController, '_issue_liveaction_delete',
        mock.MagicMock(return_value=\
            (FakeResponse('', 204, 'NO CONTENT'), False)))
    def test_get_all(self):
        actionexecution_1_id = self.__get_actionexecution_id(self.__do_post(ACTION_EXECUTION_1))
        actionexecution_2_id = self.__get_actionexecution_id(self.__do_post(ACTION_EXECUTION_2))
        resp = self.app.get('/actionexecutions')
        self.assertEqual(resp.status_int, 200)
        self.assertEquals(len(resp.json), 2,
                          '/actionexecutions did not return all '
                          'actionexecutions.')
        self.__do_delete(actionexecution_1_id)
        self.__do_delete(actionexecution_2_id)

    @mock.patch.object(
        ActionExecutionsController, '_issue_liveaction_post',
        mock.MagicMock(return_value=\
            (FakeResponse('', 200, 'OK'), False)))
    @mock.patch.object(
        ActionExecutionsController, '_issue_liveaction_delete',
        mock.MagicMock(return_value=\
            (FakeResponse('', 204, 'NO CONTENT'), False)))
    def test_get_query(self):
        actionexecution_1_id = self.__get_actionexecution_id(self.__do_post(ACTION_EXECUTION_1))
        actionexecution_2_id = self.__get_actionexecution_id(self.__do_post(ACTION_EXECUTION_2))

        resp = self.app.get('/actionexecutions?action_name=%s' %
                            ACTION_EXECUTION_1['action']['name'])
        self.assertEqual(resp.status_int, 200)
        self.assertEquals(resp.json[0]['id'], actionexecution_1_id,
                          '/actionexecutions did not return correct actionexecution.')

        resp = self.app.get('/actionexecutions?action_id=%s' %
                            self.action2['id'])
        self.assertEqual(resp.status_int, 200)
        self.assertEquals(resp.json[0]['id'], actionexecution_2_id,
                          '/actionexecutions did not return correct actionexecution.')

        self.__do_delete(actionexecution_1_id)
        self.__do_delete(actionexecution_2_id)

    @mock.patch.object(
        ActionExecutionsController, '_issue_liveaction_post',
        mock.MagicMock(return_value=\
            (FakeResponse('', 200, 'OK'), False)))
    @mock.patch.object(
        ActionExecutionsController, '_issue_liveaction_delete',
        mock.MagicMock(return_value=\
            (FakeResponse('', 204, 'NO CONTENT'), False)))
    def test_get_query_with_limit(self):
        actionexecution_1_id = self.__get_actionexecution_id(self.__do_post(ACTION_EXECUTION_1))
        actionexecution_2_id = self.__get_actionexecution_id(self.__do_post(ACTION_EXECUTION_1))

        resp = self.app.get('/actionexecutions')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 2)

        resp = self.app.get('/actionexecutions?limit=1')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 1)

        resp = self.app.get('/actionexecutions?limit=0')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 2)

        resp = self.app.get('/actionexecutions?action_name=%s' %
                            ACTION_EXECUTION_1['action']['name'])
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 2)

        resp = self.app.get('/actionexecutions?action_name=%s&limit=1' %
                            ACTION_EXECUTION_1['action']['name'])
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 1)

        resp = self.app.get('/actionexecutions?action_name=%s&limit=0' %
                            ACTION_EXECUTION_1['action']['name'])
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 2)

        self.__do_delete(actionexecution_1_id)
        self.__do_delete(actionexecution_2_id)

    def test_get_one_fail(self):
        resp = self.app.get('/actionexecutions/100', expect_errors=True)
        self.assertEqual(resp.status_int, 404)

    @mock.patch.object(
        ActionExecutionsController, '_issue_liveaction_post',
        mock.MagicMock(return_value=\
            (FakeResponse('', 200, 'OK'), False)))
    @mock.patch.object(
        ActionExecutionsController, '_issue_liveaction_delete',
        mock.MagicMock(return_value=\
            (FakeResponse('', 204, 'NO CONTENT'), False)))
    def test_post_delete(self):
        post_resp = self.__do_post(ACTION_EXECUTION_1)
        self.assertEquals(post_resp.status_int, 201)
        self.__do_delete(self.__get_actionexecution_id(post_resp))

    @mock.patch.object(
        ActionExecutionsController, '_issue_liveaction_post',
        mock.MagicMock(return_value=\
            (FakeResponse('', 200, 'OK'), False)))
    @mock.patch.object(
        ActionExecutionsController, '_issue_liveaction_delete',
        mock.MagicMock(return_value=\
            (FakeResponse('', 204, 'NO CONTENT'), False)))
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
