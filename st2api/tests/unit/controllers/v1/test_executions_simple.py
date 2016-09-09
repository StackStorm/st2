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


import bson
import copy
import datetime
import mock
import six
import uuid
try:
    import simplejson as json
except ImportError:
    import json
import st2common.validators.api.action as action_validator

from six.moves import filter
from st2common.util import isotime
from st2common.util import date as date_utils
from st2common.models.db.auth import TokenDB
from st2common.persistence.auth import Token
from st2common.persistence.trace import Trace
from st2common.services import trace as trace_service
from st2common.transport.publishers import PoolPublisher
from st2tests.fixturesloader import FixturesLoader
from tests import FunctionalTest


ACTION_1 = {
    'name': 'st2.dummy.action1',
    'description': 'test description',
    'enabled': True,
    'entry_point': '/tmp/test/action1.sh',
    'pack': 'sixpack',
    'runner_type': 'run-remote',
    'parameters': {
        'a': {
            'type': 'string',
            'default': 'abc'
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
    'pack': 'familypack',
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
    'pack': 'wolfpack',
    'runner_type': 'run-remote',
    'parameters': {
        'e': {},
        'f': {}
    }
}

ACTION_4 = {
    'name': 'st2.dummy.action4',
    'description': 'another test description',
    'enabled': True,
    'entry_point': '/tmp/test/workflows/action4.yaml',
    'pack': 'starterpack',
    'runner_type': 'mistral-v2',
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

LIVE_ACTION_1 = {
    'action': 'sixpack.st2.dummy.action1',
    'parameters': {
        'hosts': 'localhost',
        'cmd': 'uname -a'
    }
}

LIVE_ACTION_2 = {
    'action': 'familypack.st2.dummy.action2',
    'parameters': {
        'hosts': 'localhost',
        'cmd': 'ls -l'
    }
}

LIVE_ACTION_3 = {
    'action': 'wolfpack.st2.dummy.action3',
    'parameters': {
        'hosts': 'localhost',
        'cmd': 'ls -l',
        'e': 'abcde',
        'f': 12345
    }
}

LIVE_ACTION_4 = {
    'action': 'starterpack.st2.dummy.action4',
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
        post_resp = cls.app.post_json('/v1/actions', cls.action1)
        cls.action1['id'] = post_resp.json['id']

        cls.action2 = copy.deepcopy(ACTION_2)
        post_resp = cls.app.post_json('/v1/actions', cls.action2)
        cls.action2['id'] = post_resp.json['id']

        cls.action3 = copy.deepcopy(ACTION_3)
        post_resp = cls.app.post_json('/v1/actions', cls.action3)
        cls.action3['id'] = post_resp.json['id']

        cls.action4 = copy.deepcopy(ACTION_4)
        post_resp = cls.app.post_json('/v1/actions', cls.action4)
        cls.action4['id'] = post_resp.json['id']

    @classmethod
    def tearDownClass(cls):
        cls.app.delete('/v1/actions/%s' % cls.action1['id'])
        cls.app.delete('/v1/actions/%s' % cls.action2['id'])
        cls.app.delete('/v1/actions/%s' % cls.action3['id'])
        cls.app.delete('/v1/actions/%s' % cls.action4['id'])
        super(TestActionExecutionController, cls).tearDownClass()

    def test_get_one(self):
        post_resp = self._do_post(LIVE_ACTION_1)
        actionexecution_id = self._get_actionexecution_id(post_resp)
        get_resp = self._do_get_one(actionexecution_id)
        self.assertEqual(get_resp.status_int, 200)
        self.assertEqual(self._get_actionexecution_id(get_resp), actionexecution_id)
        self.assertTrue('web_url' in get_resp)
        if 'end_timestamp' in get_resp:
            self.assertTrue('elapsed_seconds' in get_resp)

    def test_get_all(self):
        self._get_actionexecution_id(self._do_post(LIVE_ACTION_1))
        self._get_actionexecution_id(self._do_post(LIVE_ACTION_2))
        resp = self.app.get('/v1/executions')
        body = resp.json
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 2,
                         '/v1/executions did not return all '
                         'actionexecutions.')
        # Assert liveactions are sorted by timestamp.
        for i in range(len(body) - 1):
            self.assertTrue(isotime.parse(body[i]['start_timestamp']) >=
                            isotime.parse(body[i + 1]['start_timestamp']))
            self.assertTrue('web_url' in body[i])
            if 'end_timestamp' in body[i]:
                self.assertTrue('elapsed_seconds' in body[i])

    def test_get_query(self):
        actionexecution_1_id = self._get_actionexecution_id(self._do_post(LIVE_ACTION_1))

        resp = self.app.get('/v1/executions?action=%s' % LIVE_ACTION_1['action'])
        self.assertEqual(resp.status_int, 200)
        matching_execution = filter(lambda ae: ae['id'] == actionexecution_1_id, resp.json)
        self.assertEqual(len(list(matching_execution)), 1,
                         '/v1/executions did not return correct liveaction.')

    def test_get_query_with_limit(self):
        self._get_actionexecution_id(self._do_post(LIVE_ACTION_1))
        self._get_actionexecution_id(self._do_post(LIVE_ACTION_1))

        resp = self.app.get('/v1/executions')
        self.assertEqual(resp.status_int, 200)
        self.assertTrue(len(resp.json) > 0)

        resp = self.app.get('/v1/executions?limit=1')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 1)

        resp = self.app.get('/v1/executions?limit=0')
        self.assertEqual(resp.status_int, 200)
        self.assertTrue(len(resp.json) > 1)

        resp = self.app.get('/v1/executions?action=%s' % LIVE_ACTION_1['action'])
        self.assertEqual(resp.status_int, 200)
        self.assertTrue(len(resp.json) > 1)

        resp = self.app.get('/v1/executions?action=%s&limit=1' %
                            LIVE_ACTION_1['action'])
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 1)

        resp = self.app.get('/v1/executions?action=%s&limit=0' %
                            LIVE_ACTION_1['action'])
        self.assertEqual(resp.status_int, 200)
        self.assertTrue(len(resp.json) > 1)

    def test_get_one_fail(self):
        resp = self.app.get('/v1/executions/100', expect_errors=True)
        self.assertEqual(resp.status_int, 404)

    def test_post_delete(self):
        post_resp = self._do_post(LIVE_ACTION_1)
        self.assertEqual(post_resp.status_int, 201)
        delete_resp = self._do_delete(self._get_actionexecution_id(post_resp))
        self.assertEqual(delete_resp.status_int, 200)
        self.assertEqual(delete_resp.json['status'], 'canceled')
        expected_result = {'message': 'Action canceled by user.', 'user': 'stanley'}
        self.assertDictEqual(delete_resp.json['result'], expected_result)

    def test_post_delete_trace(self):
        LIVE_ACTION_TRACE = copy.copy(LIVE_ACTION_1)
        LIVE_ACTION_TRACE['context'] = {'trace_context': {'trace_tag': 'balleilaka'}}
        post_resp = self._do_post(LIVE_ACTION_TRACE)
        self.assertEqual(post_resp.status_int, 201)
        delete_resp = self._do_delete(self._get_actionexecution_id(post_resp))
        self.assertEqual(delete_resp.status_int, 200)
        self.assertEqual(delete_resp.json['status'], 'canceled')
        trace_id = str(Trace.get_all()[0].id)
        LIVE_ACTION_TRACE['context'] = {'trace_context': {'id_': trace_id}}
        post_resp = self._do_post(LIVE_ACTION_TRACE)
        self.assertEqual(post_resp.status_int, 201)
        delete_resp = self._do_delete(self._get_actionexecution_id(post_resp))
        self.assertEqual(delete_resp.status_int, 200)
        self.assertEqual(delete_resp.json['status'], 'canceled')

    def test_post_parameter_validation_failed(self):
        execution = copy.deepcopy(LIVE_ACTION_1)

        # Runner type does not expects additional properties.
        execution['parameters']['foo'] = 'bar'
        post_resp = self._do_post(execution, expect_errors=True)
        self.assertEqual(post_resp.status_int, 400)
        self.assertEqual(post_resp.json['faultstring'],
                         "Additional properties are not allowed ('foo' was unexpected)")

        # Runner type expects parameter "hosts".
        execution['parameters'] = {}
        post_resp = self._do_post(execution, expect_errors=True)
        self.assertEqual(post_resp.status_int, 400)
        self.assertEqual(post_resp.json['faultstring'], "'hosts' is a required property")

        # Runner type expects parameters "cmd" to be str.
        execution['parameters'] = {"hosts": "127.0.0.1", "cmd": 1000}
        post_resp = self._do_post(execution, expect_errors=True)
        self.assertEqual(post_resp.status_int, 400)
        self.assertEqual(post_resp.json['faultstring'], "1000 is not of type 'string', 'null'")

        # Runner type expects parameters "cmd" to be str.
        execution['parameters'] = {"hosts": "127.0.0.1", "cmd": "1000", "c": 1}
        post_resp = self._do_post(execution, expect_errors=True)
        self.assertEqual(post_resp.status_int, 400)

        # Runner type permits parameters with no metadata.
        execution = copy.deepcopy(LIVE_ACTION_3)
        post_resp = self._do_post(execution, expect_errors=False)
        self.assertEqual(post_resp.status_int, 201)

    def test_post_parameter_render_failed(self):
        execution = copy.deepcopy(LIVE_ACTION_1)

        # Runner type does not expects additional properties.
        execution['parameters']['hosts'] = '{{ABSENT}}'
        post_resp = self._do_post(execution, expect_errors=True)
        self.assertEqual(post_resp.status_int, 400)
        self.assertEqual(post_resp.json['faultstring'],
                         'Dependecy unsatisfied in ABSENT')

    def test_post_parameter_validation_explicit_none(self):
        execution = copy.deepcopy(LIVE_ACTION_1)
        execution['parameters']['a'] = None
        post_resp = self._do_post(execution)
        self.assertEqual(post_resp.status_int, 201)

    def test_post_with_st2_context_in_headers(self):
        resp = self._do_post(copy.deepcopy(LIVE_ACTION_1))
        self.assertEqual(resp.status_int, 201)
        parent_user = resp.json['context']['user']
        parent_exec_id = str(resp.json['id'])
        context = {
            'parent': {
                'execution_id': parent_exec_id,
                'user': parent_user
            },
            'user': None,
            'other': {'k1': 'v1'}
        }
        headers = {'content-type': 'application/json', 'st2-context': json.dumps(context)}
        resp = self._do_post(copy.deepcopy(LIVE_ACTION_1), headers=headers)
        self.assertEqual(resp.status_int, 201)
        self.assertEqual(resp.json['context']['user'], parent_user, 'Should use parent\'s user.')
        expected = {
            'parent': {
                'execution_id': parent_exec_id,
                'user': parent_user
            },
            'user': parent_user,
            'other': {'k1': 'v1'}
        }
        self.assertDictEqual(resp.json['context'], expected)

    def test_post_with_st2_context_in_headers_failed(self):
        resp = self._do_post(copy.deepcopy(LIVE_ACTION_1))
        self.assertEqual(resp.status_int, 201)
        headers = {'content-type': 'application/json', 'st2-context': 'foobar'}
        resp = self._do_post(copy.deepcopy(LIVE_ACTION_1), headers=headers, expect_errors=True)
        self.assertEqual(resp.status_int, 400)
        self.assertIn('Unable to convert st2-context', resp.json['faultstring'])

    def test_re_run_success(self):
        # Create a new execution
        post_resp = self._do_post(LIVE_ACTION_1)
        self.assertEqual(post_resp.status_int, 201)
        execution_id = self._get_actionexecution_id(post_resp)

        # Re-run created execution (no parameters overrides)
        data = {}
        re_run_resp = self.app.post_json('/v1/executions/%s/re_run' %
                (execution_id), data)
        self.assertEqual(re_run_resp.status_int, 201)

        # Re-run created execution (with parameters overrides)
        data = {'parameters': {'a': 'val1'}}
        re_run_resp = self.app.post_json('/v1/executions/%s/re_run' % (execution_id), data)
        self.assertEqual(re_run_resp.status_int, 201)

    def test_re_run_failure_execution_doesnt_exist(self):
        # Create a new execution
        post_resp = self._do_post(LIVE_ACTION_1)
        self.assertEqual(post_resp.status_int, 201)

        # Re-run created execution (override parameter with an invalid value)
        data = {}
        re_run_resp = self.app.post_json('/v1/executions/doesntexist/re_run',
                                         data, expect_errors=True)
        self.assertEqual(re_run_resp.status_int, 404)

    def test_re_run_failure_parameter_override_invalid_type(self):
        # Create a new execution
        post_resp = self._do_post(LIVE_ACTION_1)
        self.assertEqual(post_resp.status_int, 201)
        execution_id = self._get_actionexecution_id(post_resp)

        # Re-run created execution (override parameter and task together)
        data = {'parameters': {'a': 1000}}
        re_run_resp = self.app.post_json('/v1/executions/%s/re_run' % (execution_id),
                                         data, expect_errors=True)
        self.assertEqual(re_run_resp.status_int, 400)
        self.assertIn('1000 is not of type \'string\'', re_run_resp.json['faultstring'])

    def test_re_run_workflow_success(self):
        # Create a new execution
        post_resp = self._do_post(LIVE_ACTION_4)
        self.assertEqual(post_resp.status_int, 201)
        execution_id = self._get_actionexecution_id(post_resp)

        # Re-run created execution (tasks option for non workflow)
        data = {}
        re_run_resp = self.app.post_json('/v1/executions/%s/re_run' % (execution_id),
                                         data, expect_errors=True)

        self.assertEqual(re_run_resp.status_int, 201)

        # Get the trace
        trace = trace_service.get_trace_db_by_action_execution(action_execution_id=execution_id)

        expected_context = {
            'user': 'stanley',
            're-run': {
                'ref': execution_id
            },
            'trace_context': {
                'id_': str(trace.id)
            }
        }

        self.assertDictEqual(re_run_resp.json['context'], expected_context)

    def test_re_run_workflow_task_success(self):
        # Create a new execution
        post_resp = self._do_post(LIVE_ACTION_4)
        self.assertEqual(post_resp.status_int, 201)
        execution_id = self._get_actionexecution_id(post_resp)

        # Re-run created execution (tasks option for non workflow)
        data = {'tasks': ['x']}
        re_run_resp = self.app.post_json('/v1/executions/%s/re_run' % (execution_id),
                                         data, expect_errors=True)

        self.assertEqual(re_run_resp.status_int, 201)

        # Get the trace
        trace = trace_service.get_trace_db_by_action_execution(action_execution_id=execution_id)

        expected_context = {
            'user': 'stanley',
            're-run': {
                'ref': execution_id,
                'tasks': data['tasks']
            },
            'trace_context': {
                'id_': str(trace.id)
            }
        }

        self.assertDictEqual(re_run_resp.json['context'], expected_context)

    def test_re_run_workflow_tasks_success(self):
        # Create a new execution
        post_resp = self._do_post(LIVE_ACTION_4)
        self.assertEqual(post_resp.status_int, 201)
        execution_id = self._get_actionexecution_id(post_resp)

        # Re-run created execution (tasks option for non workflow)
        data = {'tasks': ['x', 'y']}
        re_run_resp = self.app.post_json('/v1/executions/%s/re_run' % (execution_id),
                                         data, expect_errors=True)

        self.assertEqual(re_run_resp.status_int, 201)

        # Get the trace
        trace = trace_service.get_trace_db_by_action_execution(action_execution_id=execution_id)

        expected_context = {
            'user': 'stanley',
            're-run': {
                'ref': execution_id,
                'tasks': data['tasks']
            },
            'trace_context': {
                'id_': str(trace.id)
            }
        }

        self.assertDictEqual(re_run_resp.json['context'], expected_context)

    def test_re_run_workflow_tasks_reset_success(self):
        # Create a new execution
        post_resp = self._do_post(LIVE_ACTION_4)
        self.assertEqual(post_resp.status_int, 201)
        execution_id = self._get_actionexecution_id(post_resp)

        # Re-run created execution (tasks option for non workflow)
        data = {'tasks': ['x', 'y'], 'reset': ['y']}
        re_run_resp = self.app.post_json('/v1/executions/%s/re_run' % (execution_id),
                                         data, expect_errors=True)

        self.assertEqual(re_run_resp.status_int, 201)

        # Get the trace
        trace = trace_service.get_trace_db_by_action_execution(action_execution_id=execution_id)

        expected_context = {
            'user': 'stanley',
            're-run': {
                'ref': execution_id,
                'tasks': data['tasks'],
                'reset': data['reset']
            },
            'trace_context': {
                'id_': str(trace.id)
            }
        }

        self.assertDictEqual(re_run_resp.json['context'], expected_context)

    def test_re_run_failure_tasks_option_for_non_workflow(self):
        # Create a new execution
        post_resp = self._do_post(LIVE_ACTION_1)
        self.assertEqual(post_resp.status_int, 201)
        execution_id = self._get_actionexecution_id(post_resp)

        # Re-run created execution (tasks option for non workflow)
        data = {'tasks': ['x']}
        re_run_resp = self.app.post_json('/v1/executions/%s/re_run' % (execution_id),
                                         data, expect_errors=True)

        self.assertEqual(re_run_resp.status_int, 400)
        self.assertIn('only supported for Mistral workflows', re_run_resp.json['faultstring'])

    def test_re_run_workflow_failure_given_both_params_and_tasks(self):
        # Create a new execution
        post_resp = self._do_post(LIVE_ACTION_4)
        self.assertEqual(post_resp.status_int, 201)
        execution_id = self._get_actionexecution_id(post_resp)

        # Re-run created execution (override parameter with an invalid value)
        data = {'parameters': {'a': 'xyz'}, 'tasks': ['x']}
        re_run_resp = self.app.post_json('/v1/executions/%s/re_run' % (execution_id),
                                         data, expect_errors=True)

        self.assertEqual(re_run_resp.status_int, 400)
        self.assertIn('not supported when re-running task(s) for a workflow',
                      re_run_resp.json['faultstring'])

    def test_re_run_workflow_failure_given_both_params_and_reset_tasks(self):
        # Create a new execution
        post_resp = self._do_post(LIVE_ACTION_4)
        self.assertEqual(post_resp.status_int, 201)
        execution_id = self._get_actionexecution_id(post_resp)

        # Re-run created execution (override parameter with an invalid value)
        data = {'parameters': {'a': 'xyz'}, 'reset': ['x']}
        re_run_resp = self.app.post_json('/v1/executions/%s/re_run' % (execution_id),
                                         data, expect_errors=True)

        self.assertEqual(re_run_resp.status_int, 400)
        self.assertIn('not supported when re-running task(s) for a workflow',
                      re_run_resp.json['faultstring'])

    def test_re_run_workflow_failure_invalid_reset_tasks(self):
        # Create a new execution
        post_resp = self._do_post(LIVE_ACTION_4)
        self.assertEqual(post_resp.status_int, 201)
        execution_id = self._get_actionexecution_id(post_resp)

        # Re-run created execution (override parameter with an invalid value)
        data = {'tasks': ['x'], 'reset': ['y']}
        re_run_resp = self.app.post_json('/v1/executions/%s/re_run' % (execution_id),
                                         data, expect_errors=True)

        self.assertEqual(re_run_resp.status_int, 400)
        self.assertIn('tasks to reset does not match the tasks to rerun',
                      re_run_resp.json['faultstring'])

    @staticmethod
    def _get_actionexecution_id(resp):
        return resp.json['id']

    def _do_get_one(self, actionexecution_id, *args, **kwargs):
        return self.app.get('/v1/executions/%s' % actionexecution_id, *args, **kwargs)

    def _do_post(self, liveaction, *args, **kwargs):
        return self.app.post_json('/v1/executions', liveaction, *args, **kwargs)

    def _do_delete(self, actionexecution_id, expect_errors=False):
        return self.app.delete('/v1/executions/%s' % actionexecution_id,
                               expect_errors=expect_errors)


# TestActionExecutionControllerAuthEnabled test section

NOW = date_utils.get_datetime_utc_now()
EXPIRY = NOW + datetime.timedelta(seconds=300)
SYS_TOKEN = TokenDB(id=bson.ObjectId(), user='system', token=uuid.uuid4().hex, expiry=EXPIRY)
USR_TOKEN = TokenDB(id=bson.ObjectId(), user='tokenuser', token=uuid.uuid4().hex, expiry=EXPIRY)

FIXTURES_PACK = 'generic'
FIXTURES = {
    'users': ['system_user.yaml', 'token_user.yaml']
}


def mock_get_token(*args, **kwargs):
    if args[0] == SYS_TOKEN.token:
        return SYS_TOKEN
    return USR_TOKEN


@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
class TestActionExecutionControllerAuthEnabled(FunctionalTest):

    enable_auth = True

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
        post_resp = cls.app.post_json('/v1/actions', cls.action, headers=headers)
        cls.action['id'] = post_resp.json['id']

        FixturesLoader().save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                             fixtures_dict=FIXTURES)

    @classmethod
    @mock.patch.object(
        Token, 'get',
        mock.MagicMock(side_effect=mock_get_token))
    def tearDownClass(cls):
        headers = {'content-type': 'application/json', 'X-Auth-Token': str(SYS_TOKEN.token)}
        cls.app.delete('/v1/actions/%s' % cls.action['id'], headers=headers)
        super(TestActionExecutionControllerAuthEnabled, cls).tearDownClass()

    def _do_post(self, liveaction, *args, **kwargs):
        return self.app.post_json('/v1/executions', liveaction, *args, **kwargs)

    @mock.patch.object(
        Token, 'get',
        mock.MagicMock(side_effect=mock_get_token))
    def test_post_with_st2_context_in_headers(self):
        headers = {'content-type': 'application/json', 'X-Auth-Token': str(USR_TOKEN.token)}
        resp = self._do_post(copy.deepcopy(LIVE_ACTION_1), headers=headers)
        self.assertEqual(resp.status_int, 201)
        token_user = resp.json['context']['user']
        self.assertEqual(token_user, 'tokenuser')
        context = {'parent': {'execution_id': str(resp.json['id']), 'user': token_user}}
        headers = {'content-type': 'application/json',
                   'X-Auth-Token': str(SYS_TOKEN.token),
                   'st2-context': json.dumps(context)}
        resp = self._do_post(copy.deepcopy(LIVE_ACTION_1), headers=headers)
        self.assertEqual(resp.status_int, 201)
        self.assertEqual(resp.json['context']['user'], 'tokenuser')
        self.assertEqual(resp.json['context']['parent'], context['parent'])


# descendants test section

DESCENDANTS_PACK = 'descendants'

DESCENDANTS_FIXTURES = {
    'executions': ['root_execution.yaml', 'child1_level1.yaml', 'child2_level1.yaml',
                   'child1_level2.yaml', 'child2_level2.yaml', 'child3_level2.yaml',
                   'child1_level3.yaml', 'child2_level3.yaml', 'child3_level3.yaml']
}


class TestActionExecutionControllerDescendantsTest(FunctionalTest):

    @classmethod
    def setUpClass(cls):
        super(TestActionExecutionControllerDescendantsTest, cls).setUpClass()
        cls.MODELS = FixturesLoader().save_fixtures_to_db(fixtures_pack=DESCENDANTS_PACK,
                                                          fixtures_dict=DESCENDANTS_FIXTURES)

    def test_get_all_descendants(self):
        root_execution = self.MODELS['executions']['root_execution.yaml']
        resp = self.app.get('/v1/executions/%s/children' % str(root_execution.id))
        self.assertEqual(resp.status_int, 200)

        all_descendants_ids = [descendant['id'] for descendant in resp.json]
        all_descendants_ids.sort()

        # everything except the root_execution
        expected_ids = [str(v.id) for _, v in six.iteritems(self.MODELS['executions'])
                        if v.id != root_execution.id]
        expected_ids.sort()

        self.assertListEqual(all_descendants_ids, expected_ids)

    def test_get_all_descendants_depth_neg_1(self):
        root_execution = self.MODELS['executions']['root_execution.yaml']
        resp = self.app.get('/v1/executions/%s/children?depth=-1' % str(root_execution.id))
        self.assertEqual(resp.status_int, 200)

        all_descendants_ids = [descendant['id'] for descendant in resp.json]
        all_descendants_ids.sort()

        # everything except the root_execution
        expected_ids = [str(v.id) for _, v in six.iteritems(self.MODELS['executions'])
                        if v.id != root_execution.id]
        expected_ids.sort()

        self.assertListEqual(all_descendants_ids, expected_ids)

    def test_get_1_level_descendants(self):
        root_execution = self.MODELS['executions']['root_execution.yaml']
        resp = self.app.get('/v1/executions/%s/children?depth=1' % str(root_execution.id))
        self.assertEqual(resp.status_int, 200)

        all_descendants_ids = [descendant['id'] for descendant in resp.json]
        all_descendants_ids.sort()

        # All children of root_execution
        expected_ids = [str(v.id) for _, v in six.iteritems(self.MODELS['executions'])
                        if v.parent == str(root_execution.id)]
        expected_ids.sort()

        self.assertListEqual(all_descendants_ids, expected_ids)
