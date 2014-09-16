import copy
from six.moves import filter
try:
    import simplejson as json
except ImportError:
    import json
import mock

from st2api.controllers.actions import ActionsController
from st2common.transport.publishers import PoolPublisher
from tests import FunctionalTest


ACTION_1 = {
    'name': 'st2.dummy.action1',
    'description': 'test description',
    'enabled': True,
    'entry_point': '/tmp/test/action1.sh',
    'content_pack': 'sixpack',
    'runner_type': 'run-remote',
    'parameters': {
        'a': {
            'type': 'string',
            'default': 'abc'
        },
        'b': {
            'type': 'number',
            'default': 123
        }
    }
}

ACTION_2 = {
    'name': 'st2.dummy.action2',
    'description': 'another test description',
    'enabled': True,
    'entry_point': '/tmp/test/action2.sh',
    'content_pack': 'familypack',
    'runner_type': 'run-remote',
    'parameters': {
        'c': {
            'type': 'object',
            'properties': {
                'c1': {
                    'type': 'string'
                }
            }
        },
        'd': {
            'type': 'boolean',
            'default': False
        }
    }
}

ACTION_3 = {
    'name': 'st2.dummy.action3',
    'description': 'another test description',
    'enabled': True,
    'entry_point': '/tmp/test/action3.sh',
    'content_pack': 'wolfpack',
    'runner_type': 'run-remote',
    'parameters': {
        'e': {},
        'f': {}
    }
}

ACTION_EXECUTION_1 = {
    'action': {'name': 'st2.dummy.action1'},
    'parameters': {
        'hosts': 'localhost',
        'cmd': 'uname -a'
    }
}

ACTION_EXECUTION_2 = {
    'action': {'name': 'st2.dummy.action2'},
    'parameters': {
        'hosts': 'localhost',
        'cmd': 'ls -l'
    }
}

ACTION_EXECUTION_3 = {
    'action': {'name': 'st2.dummy.action3'},
    'parameters': {
        'hosts': 'localhost',
        'cmd': 'ls -l',
        'e': 'abcde',
        'f': 12345
    }
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


@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
class TestActionExecutionsController(FunctionalTest):

    @classmethod
    @mock.patch.object(ActionsController, '_is_valid_content_pack', mock.MagicMock(
        return_value=True))
    def setUpClass(cls):
        super(TestActionExecutionsController, cls).setUpClass()
        cls.action1 = copy.copy(ACTION_1)
        post_resp = cls.app.post_json('/actions', cls.action1)
        cls.action1['id'] = post_resp.json['id']
        cls.action2 = copy.copy(ACTION_2)
        post_resp = cls.app.post_json('/actions', cls.action2)
        cls.action2['id'] = post_resp.json['id']
        cls.action3 = copy.copy(ACTION_3)
        post_resp = cls.app.post_json('/actions', cls.action3)
        cls.action3['id'] = post_resp.json['id']

    @classmethod
    def tearDownClass(cls):
        cls.app.delete('/actions/%s' % cls.action1['id'])
        cls.app.delete('/actions/%s' % cls.action2['id'])
        super(TestActionExecutionsController, cls).tearDownClass()

    def test_get_one(self):
        post_resp = self.__do_post(ACTION_EXECUTION_1)
        actionexecution_id = self.__get_actionexecution_id(post_resp)
        get_resp = self.__do_get_one(actionexecution_id)
        self.assertEquals(get_resp.status_int, 200)
        self.assertEquals(self.__get_actionexecution_id(get_resp), actionexecution_id)

    def test_get_all(self):
        self.__get_actionexecution_id(self.__do_post(ACTION_EXECUTION_1))
        self.__get_actionexecution_id(self.__do_post(ACTION_EXECUTION_2))
        resp = self.app.get('/actionexecutions')
        self.assertEqual(resp.status_int, 200)
        self.assertEquals(len(resp.json), 2,
                          '/actionexecutions did not return all '
                          'actionexecutions.')

    def test_get_query(self):
        actionexecution_1_id = self.__get_actionexecution_id(self.__do_post(ACTION_EXECUTION_1))
        actionexecution_2_id = self.__get_actionexecution_id(self.__do_post(ACTION_EXECUTION_2))

        resp = self.app.get('/actionexecutions?action_name=%s' %
                            ACTION_EXECUTION_1['action']['name'])
        self.assertEqual(resp.status_int, 200)
        matching_execution = filter(lambda ae: ae['id'] == actionexecution_1_id, resp.json)
        self.assertEquals(len(list(matching_execution)), 1,
                          '/actionexecutions did not return correct actionexecution.')

        resp = self.app.get('/actionexecutions?action_id=%s' %
                            self.action2['id'])
        self.assertEqual(resp.status_int, 200)
        matching_execution = filter(lambda ae: ae['id'] == actionexecution_2_id, resp.json)
        self.assertEquals(len(list(matching_execution)), 1,
                          '/actionexecutions did not return correct actionexecution.')

    def test_get_query_with_limit(self):
        self.__get_actionexecution_id(self.__do_post(ACTION_EXECUTION_1))
        self.__get_actionexecution_id(self.__do_post(ACTION_EXECUTION_1))

        resp = self.app.get('/actionexecutions')
        self.assertEqual(resp.status_int, 200)
        self.assertTrue(len(resp.json) > 0)

        resp = self.app.get('/actionexecutions?limit=1')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 1)

        resp = self.app.get('/actionexecutions?limit=0')
        self.assertEqual(resp.status_int, 200)
        self.assertTrue(len(resp.json) > 1)

        resp = self.app.get('/actionexecutions?action_name=%s' %
                            ACTION_EXECUTION_1['action']['name'])
        self.assertEqual(resp.status_int, 200)
        self.assertTrue(len(resp.json) > 1)

        resp = self.app.get('/actionexecutions?action_name=%s&limit=1' %
                            ACTION_EXECUTION_1['action']['name'])
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 1)

        resp = self.app.get('/actionexecutions?action_name=%s&limit=0' %
                            ACTION_EXECUTION_1['action']['name'])
        self.assertEqual(resp.status_int, 200)
        self.assertTrue(len(resp.json) > 1)

    def test_get_one_fail(self):
        resp = self.app.get('/actionexecutions/100', expect_errors=True)
        self.assertEqual(resp.status_int, 404)

    def test_post_delete(self):
        post_resp = self.__do_post(ACTION_EXECUTION_1)
        self.assertEquals(post_resp.status_int, 201)

    def test_post_parameter_validation_failed(self):
        execution = copy.copy(ACTION_EXECUTION_1)

        # Runner type does not expects additional properties.
        execution['parameters']['foo'] = 'bar'
        post_resp = self.__do_post(execution, expect_errors=True)
        self.assertEquals(post_resp.status_int, 400)

        # Runner type expects parameter "hosts".
        execution['parameters'] = {}
        post_resp = self.__do_post(execution, expect_errors=True)
        self.assertEquals(post_resp.status_int, 400)

        # Runner type expects parameters "cmd" to be str.
        execution['parameters'] = {"hosts": "localhost", "cmd": 1000}
        post_resp = self.__do_post(execution, expect_errors=True)
        self.assertEquals(post_resp.status_int, 400)

        # Runner type permits parameters with no metadata.
        execution = copy.copy(ACTION_EXECUTION_3)
        post_resp = self.__do_post(execution, expect_errors=False)
        self.assertEquals(post_resp.status_int, 201)

    @staticmethod
    def __get_actionexecution_id(resp):
        return resp.json['id']

    def __do_get_one(self, actionexecution_id, expect_errors=False):
        return self.app.get('/actionexecutions/%s' % actionexecution_id,
                            expect_errors=expect_errors)

    def __do_post(self, actionexecution, expect_errors=False):
        return self.app.post_json('/actionexecutions', actionexecution,
                                  expect_errors=expect_errors)
