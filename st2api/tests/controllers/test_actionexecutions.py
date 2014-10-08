import uuid
import copy
import datetime

import bson
import mock
from six.moves import filter
try:
    import simplejson as json
except ImportError:
    import json

from st2common.models.db.access import TokenDB
from st2common.persistence.access import Token
from st2common.transport.publishers import PoolPublisher
import st2common.validators.api.action as action_validator
from tests import FunctionalTest, AuthMiddlewareTest


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
            'default': 'abc',
            'optional': False
        },
        'b': {
            'type': 'number',
            'default': 123
        },
        'c': {
            'type': 'number',
            'default': 123,
            'immutable': True
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
class TestActionExecutionController(FunctionalTest):

    @classmethod
    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    def setUpClass(cls):
        super(TestActionExecutionController, cls).setUpClass()
        cls.action1 = copy.deepcopy(ACTION_1)
        print(cls.action1)
        post_resp = cls.app.post_json('/actions', cls.action1)
        cls.action1['id'] = post_resp.json['id']
        cls.action2 = copy.deepcopy(ACTION_2)
        post_resp = cls.app.post_json('/actions', cls.action2)
        cls.action2['id'] = post_resp.json['id']
        cls.action3 = copy.deepcopy(ACTION_3)
        post_resp = cls.app.post_json('/actions', cls.action3)
        cls.action3['id'] = post_resp.json['id']

    @classmethod
    def tearDownClass(cls):
        cls.app.delete('/actions/%s' % cls.action1['id'])
        cls.app.delete('/actions/%s' % cls.action2['id'])
        cls.app.delete('/actions/%s' % cls.action3['id'])
        super(TestActionExecutionController, cls).tearDownClass()

    def test_get_one(self):
        post_resp = self._do_post(ACTION_EXECUTION_1)
        actionexecution_id = self._get_actionexecution_id(post_resp)
        get_resp = self._do_get_one(actionexecution_id)
        self.assertEqual(get_resp.status_int, 200)
        self.assertEqual(self._get_actionexecution_id(get_resp), actionexecution_id)

    def test_get_all(self):
        self._get_actionexecution_id(self._do_post(ACTION_EXECUTION_1))
        self._get_actionexecution_id(self._do_post(ACTION_EXECUTION_2))
        resp = self.app.get('/actionexecutions')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 2,
                         '/actionexecutions did not return all '
                         'actionexecutions.')

    def test_get_query(self):
        actionexecution_1_id = self._get_actionexecution_id(self._do_post(ACTION_EXECUTION_1))
        actionexecution_2_id = self._get_actionexecution_id(self._do_post(ACTION_EXECUTION_2))

        resp = self.app.get('/actionexecutions?action_name=%s' %
                            ACTION_EXECUTION_1['action']['name'])
        self.assertEqual(resp.status_int, 200)
        matching_execution = filter(lambda ae: ae['id'] == actionexecution_1_id, resp.json)
        self.assertEqual(len(list(matching_execution)), 1,
                         '/actionexecutions did not return correct actionexecution.')

        resp = self.app.get('/actionexecutions?action_id=%s' %
                            self.action2['id'])
        self.assertEqual(resp.status_int, 200)
        matching_execution = filter(lambda ae: ae['id'] == actionexecution_2_id, resp.json)
        self.assertEqual(len(list(matching_execution)), 1,
                         '/actionexecutions did not return correct actionexecution.')

    def test_get_query_with_limit(self):
        self._get_actionexecution_id(self._do_post(ACTION_EXECUTION_1))
        self._get_actionexecution_id(self._do_post(ACTION_EXECUTION_1))

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
        post_resp = self._do_post(ACTION_EXECUTION_1)
        self.assertEqual(post_resp.status_int, 201)

    def test_post_parameter_validation_failed(self):
        execution = copy.deepcopy(ACTION_EXECUTION_1)

        # Runner type does not expects additional properties.
        execution['parameters']['foo'] = 'bar'
        post_resp = self._do_post(execution, expect_errors=True)
        self.assertEqual(post_resp.status_int, 400)

        # Runner type expects parameter "hosts".
        execution['parameters'] = {}
        post_resp = self._do_post(execution, expect_errors=True)
        self.assertEqual(post_resp.status_int, 400)

        # Runner type expects parameters "cmd" to be str.
        execution['parameters'] = {"hosts": "localhost", "cmd": 1000}
        post_resp = self._do_post(execution, expect_errors=True)
        self.assertEqual(post_resp.status_int, 400)

        # Runner type expects parameters "cmd" to be str.
        execution['parameters'] = {"hosts": "localhost", "cmd": "1000", "c": 1}
        post_resp = self._do_post(execution, expect_errors=True)
        self.assertEqual(post_resp.status_int, 400)

        # Runner type permits parameters with no metadata.
        execution = copy.deepcopy(ACTION_EXECUTION_3)
        post_resp = self._do_post(execution, expect_errors=False)
        self.assertEqual(post_resp.status_int, 201)

    def test_post_with_st2_context_in_headers(self):
        resp = self._do_post(copy.deepcopy(ACTION_EXECUTION_1))
        self.assertEqual(resp.status_int, 201)
        context = {'parent': str(resp.json['id']), 'user': None}
        headers = {'content-type': 'application/json', 'st2-context': json.dumps(context)}
        resp = self._do_post(copy.deepcopy(ACTION_EXECUTION_1), headers=headers)
        self.assertEqual(resp.status_int, 201)
        self.assertIsNone(resp.json['context']['user'])
        self.assertDictEqual(resp.json['context'], context)

    @staticmethod
    def _get_actionexecution_id(resp):
        return resp.json['id']

    def _do_get_one(self, actionexecution_id, *args, **kwargs):
        return self.app.get('/actionexecutions/%s' % actionexecution_id, *args, **kwargs)

    def _do_post(self, actionexecution, *args, **kwargs):
        return self.app.post_json('/actionexecutions', actionexecution, *args, **kwargs)


EXPIRY = datetime.datetime.now() + datetime.timedelta(seconds=300)
SYS_TOKEN = TokenDB(id=bson.ObjectId(), user='system', token=uuid.uuid4().hex, expiry=EXPIRY)
USR_TOKEN = TokenDB(id=bson.ObjectId(), user='stanley', token=uuid.uuid4().hex, expiry=EXPIRY)


def mock_get_token(*args, **kwargs):
    if args[0] == SYS_TOKEN.token:
        return SYS_TOKEN
    return USR_TOKEN


@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
class TestActionExecutionControllerAuthEnabled(AuthMiddlewareTest):

    @classmethod
    @mock.patch.object(
        Token, 'get',
        mock.MagicMock(side_effect=mock_get_token))
    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    def setUpClass(cls):
        super(TestActionExecutionControllerAuthEnabled, cls).setUpClass()
        cls.action = copy.deepcopy(ACTION_1)
        headers = {'content-type': 'application/json', 'X-Auth-Token': str(SYS_TOKEN.token)}
        post_resp = cls.app.post_json('/actions', cls.action, headers=headers)
        cls.action['id'] = post_resp.json['id']

    @classmethod
    @mock.patch.object(
        Token, 'get',
        mock.MagicMock(side_effect=mock_get_token))
    def tearDownClass(cls):
        headers = {'content-type': 'application/json', 'X-Auth-Token': str(SYS_TOKEN.token)}
        cls.app.delete('/actions/%s' % cls.action['id'], headers=headers)
        super(TestActionExecutionControllerAuthEnabled, cls).tearDownClass()

    def _do_post(self, actionexecution, *args, **kwargs):
        return self.app.post_json('/actionexecutions', actionexecution, *args, **kwargs)

    @mock.patch.object(
        Token, 'get',
        mock.MagicMock(side_effect=mock_get_token))
    def test_post_with_st2_context_in_headers(self):
        headers = {'content-type': 'application/json', 'X-Auth-Token': str(USR_TOKEN.token)}
        resp = self._do_post(copy.deepcopy(ACTION_EXECUTION_1), headers=headers)
        self.assertEqual(resp.status_int, 201)
        self.assertEqual(resp.json['context']['user'], 'stanley')
        context = {'parent': str(resp.json['id'])}
        headers = {'content-type': 'application/json',
                   'X-Auth-Token': str(SYS_TOKEN.token),
                   'st2-context': json.dumps(context)}
        resp = self._do_post(copy.deepcopy(ACTION_EXECUTION_1), headers=headers)
        self.assertEqual(resp.status_int, 201)
        self.assertEqual(resp.json['context']['user'], 'stanley')
        self.assertEqual(resp.json['context']['parent'], context['parent'])
