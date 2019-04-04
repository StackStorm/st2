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
import mock

try:
    import simplejson as json
except ImportError:
    import json

from six.moves import filter
from six.moves import http_client

from st2common.constants import action as action_constants
from st2common.constants.secrets import MASKED_ATTRIBUTE_VALUE
from st2common.content import utils as content_utils
from st2common.models.db.execution import ActionExecutionDB
from st2common.models.db.execution import ActionExecutionOutputDB
from st2common.persistence.execution import ActionExecution
from st2common.persistence.execution import ActionExecutionOutput
from st2common.persistence.liveaction import LiveAction
from st2common.persistence.trace import Trace
from st2common.services import action as action_service
from st2common.services import trace as trace_service
from st2common.transport.publishers import PoolPublisher
from st2common.util import action_db as action_db_util
from st2common.util import isotime
from st2common.util import date as date_utils
from st2api.controllers.v1.actionexecutions import ActionExecutionsController
import st2common.validators.api.action as action_validator
from st2tests.api import BaseActionExecutionControllerTestCase
from st2tests.api import SUPER_SECRET_PARAMETER
from st2tests.api import ANOTHER_SUPER_SECRET_PARAMETER

from st2tests.api import FunctionalTest
from st2tests.api import APIControllerWithIncludeAndExcludeFilterTestCase

__all__ = [
    'ActionExecutionControllerTestCase',
    'ActionExecutionOutputControllerTestCase'
]


ACTION_1 = {
    'name': 'st2.dummy.action1',
    'description': 'test description',
    'enabled': True,
    'entry_point': '/tmp/test/action1.sh',
    'pack': 'sixpack',
    'runner_type': 'remote-shell-cmd',
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
        },
        'd': {
            'type': 'string',
            'secret': True
        }
    }
}

ACTION_2 = {
    'name': 'st2.dummy.action2',
    'description': 'another test description',
    'enabled': True,
    'entry_point': '/tmp/test/action2.sh',
    'pack': 'familypack',
    'runner_type': 'remote-shell-cmd',
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
    'runner_type': 'remote-shell-cmd',
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

ACTION_INQUIRY = {
    'name': 'st2.dummy.ask',
    'description': 'another test description',
    'enabled': True,
    'pack': 'wolfpack',
    'runner_type': 'inquirer',
}

ACTION_DEFAULT_TEMPLATE = {
    'name': 'st2.dummy.default_template',
    'description': 'An action that uses a jinja template as a default value for a parameter',
    'enabled': True,
    'pack': 'starterpack',
    'runner_type': 'local-shell-cmd',
    'parameters': {
        'intparam': {
            'type': 'integer',
            'default': '{{ st2kv.system.test_int | int }}'
        }
    }
}

LIVE_ACTION_1 = {
    'action': 'sixpack.st2.dummy.action1',
    'parameters': {
        'hosts': 'localhost',
        'cmd': 'uname -a',
        'd': SUPER_SECRET_PARAMETER
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

LIVE_ACTION_DELAY = {
    'action': 'sixpack.st2.dummy.action1',
    'parameters': {
        'hosts': 'localhost',
        'cmd': 'uname -a',
        'd': SUPER_SECRET_PARAMETER
    },
    'delay': 100
}


LIVE_ACTION_INQUIRY = {
    'parameters': {
        'route': 'developers',
        'schema': {
            'type': 'object',
            'properties': {
                'secondfactor': {
                    'secret': True,
                    'required': True,
                    'type': u'string',
                    'description': 'Please enter second factor for authenticating to "foo" service'
                }
            }
        }
    },
    'action': 'wolfpack.st2.dummy.ask',
    'result': {
        'users': [],
        'roles': [],
        'route': 'developers',
        'ttl': 1440,
        'response': {
            'secondfactor': 'supersecretvalue'
        },
        'schema': {
            'type': 'object',
            'properties': {
                'secondfactor': {
                    'secret': True,
                    'required': True,
                    'type': 'string',
                    'description': 'Please enter second factor for authenticating to "foo" service'
                }
            }
        }
    }
}
LIVE_ACTION_WITH_SECRET_PARAM = {
    'parameters': {
        # action params
        'a': 'param a',
        'd': 'secretpassword1',

        # runner params
        'password': 'secretpassword2',
        'hosts': 'localhost'
    },
    'action': 'sixpack.st2.dummy.action1'
}

# Do not add parameters to this. There are tests that will test first without params,
# then make a copy with params.
LIVE_ACTION_DEFAULT_TEMPLATE = {
    'action': 'starterpack.st2.dummy.default_template',
}

FIXTURES_PACK = 'generic'
TEST_FIXTURES = {
    'runners': ['testrunner1.yaml'],
    'actions': ['action1.yaml', 'local.yaml']
}


@mock.patch.object(content_utils, 'get_pack_base_path', mock.MagicMock(return_value='/tmp/test'))
@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
class ActionExecutionControllerTestCase(BaseActionExecutionControllerTestCase, FunctionalTest,
                                        APIControllerWithIncludeAndExcludeFilterTestCase):
    get_all_path = '/v1/executions'
    controller_cls = ActionExecutionsController
    include_attribute_field_name = 'status'
    exclude_attribute_field_name = 'status'
    test_exact_object_count = False

    @classmethod
    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    def setUpClass(cls):
        super(BaseActionExecutionControllerTestCase, cls).setUpClass()

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

        cls.action_inquiry = copy.deepcopy(ACTION_INQUIRY)
        post_resp = cls.app.post_json('/v1/actions', cls.action_inquiry)
        cls.action_inquiry['id'] = post_resp.json['id']

        cls.action_template = copy.deepcopy(ACTION_DEFAULT_TEMPLATE)
        post_resp = cls.app.post_json('/v1/actions', cls.action_template)
        cls.action_template['id'] = post_resp.json['id']

    @classmethod
    def tearDownClass(cls):
        cls.app.delete('/v1/actions/%s' % cls.action1['id'])
        cls.app.delete('/v1/actions/%s' % cls.action2['id'])
        cls.app.delete('/v1/actions/%s' % cls.action3['id'])
        cls.app.delete('/v1/actions/%s' % cls.action4['id'])
        cls.app.delete('/v1/actions/%s' % cls.action_inquiry['id'])
        cls.app.delete('/v1/actions/%s' % cls.action_template['id'])
        super(BaseActionExecutionControllerTestCase, cls).tearDownClass()

    def test_get_one(self):
        post_resp = self._do_post(LIVE_ACTION_1)
        actionexecution_id = self._get_actionexecution_id(post_resp)
        get_resp = self._do_get_one(actionexecution_id)
        self.assertEqual(get_resp.status_int, 200)
        self.assertEqual(self._get_actionexecution_id(get_resp), actionexecution_id)
        self.assertTrue('web_url' in get_resp)
        if 'end_timestamp' in get_resp:
            self.assertTrue('elapsed_seconds' in get_resp)

        get_resp = self._do_get_one('last')
        self.assertEqual(get_resp.status_int, 200)
        self.assertEqual(self._get_actionexecution_id(get_resp), actionexecution_id)

    def test_get_all_id_query_param_filtering_success(self):
        post_resp = self._do_post(LIVE_ACTION_1)
        actionexecution_id = self._get_actionexecution_id(post_resp)
        get_resp = self._do_get_one(actionexecution_id)
        self.assertEqual(get_resp.status_int, 200)
        self.assertEqual(self._get_actionexecution_id(get_resp), actionexecution_id)

        resp = self.app.get('/v1/executions?id=%s' % (actionexecution_id), expect_errors=False)
        self.assertEqual(resp.status_int, 200)

    def test_get_all_id_query_param_filtering_invalid_id(self):
        resp = self.app.get('/v1/executions?id=invalidid', expect_errors=True)
        self.assertEqual(resp.status_int, 400)
        self.assertTrue('not a valid ObjectId' in resp.json['faultstring'])

    def test_get_all_id_query_param_filtering_multiple_ids_provided(self):
        post_resp = self._do_post(LIVE_ACTION_1)
        self.assertEqual(post_resp.status_int, 201)
        id_1 = self._get_actionexecution_id(post_resp)

        post_resp = self._do_post(LIVE_ACTION_1)
        self.assertEqual(post_resp.status_int, 201)
        id_2 = self._get_actionexecution_id(post_resp)

        resp = self.app.get('/v1/executions?id=%s,%s' % (id_1, id_2), expect_errors=False)
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 2)

    def test_get_all(self):
        self._get_actionexecution_id(self._do_post(LIVE_ACTION_1))
        self._get_actionexecution_id(self._do_post(LIVE_ACTION_2))
        resp = self.app.get('/v1/executions')
        body = resp.json
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.headers['X-Total-Count'], "2")
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

    def test_get_all_invalid_offset_too_large(self):
        offset = '2141564789454123457895412237483648'
        resp = self.app.get('/v1/executions?offset=%s&limit=1' % (offset), expect_errors=True)
        self.assertEqual(resp.status_int, 400)
        self.assertEqual(resp.json['faultstring'],
                         u'Offset "%s" specified is more than 32-bit int' % (offset))

    def test_get_query(self):
        actionexecution_1_id = self._get_actionexecution_id(self._do_post(LIVE_ACTION_1))

        resp = self.app.get('/v1/executions?action=%s' % LIVE_ACTION_1['action'])
        self.assertEqual(resp.status_int, 200)
        matching_execution = filter(lambda ae: ae['id'] == actionexecution_1_id, resp.json)
        self.assertEqual(len(list(matching_execution)), 1,
                         '/v1/executions did not return correct liveaction.')

    def test_get_query_with_limit_and_offset(self):
        self._get_actionexecution_id(self._do_post(LIVE_ACTION_1))
        self._get_actionexecution_id(self._do_post(LIVE_ACTION_1))

        resp = self.app.get('/v1/executions')
        self.assertEqual(resp.status_int, 200)
        self.assertTrue(len(resp.json) > 0)

        resp = self.app.get('/v1/executions?limit=1')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 1)

        resp = self.app.get('/v1/executions?limit=0', expect_errors=True)
        self.assertEqual(resp.status_int, 400)
        self.assertTrue(resp.json['faultstring'],
                        u'Limit, "0" specified, must be a positive number or -1 for full \
                        result set.')

        resp = self.app.get('/v1/executions?limit=-1')
        self.assertEqual(resp.status_int, 200)
        self.assertTrue(len(resp.json) > 1)

        resp = self.app.get('/v1/executions?limit=-22', expect_errors=True)
        self.assertEqual(resp.status_int, 400)
        self.assertEqual(resp.json['faultstring'],
                         u'Limit, "-22" specified, must be a positive number.')

        resp = self.app.get('/v1/executions?action=%s' % LIVE_ACTION_1['action'])
        self.assertEqual(resp.status_int, 200)
        self.assertTrue(len(resp.json) > 1)

        resp = self.app.get('/v1/executions?action=%s&limit=0' %
                            LIVE_ACTION_1['action'], expect_errors=True)
        self.assertEqual(resp.status_int, 400)
        self.assertTrue(resp.json['faultstring'],
                        u'Limit, "0" specified, must be a positive number or -1 for full \
                        result set.')

        resp = self.app.get('/v1/executions?action=%s&limit=1' %
                            LIVE_ACTION_1['action'])
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 1)
        total_count = resp.headers['X-Total-Count']

        resp = self.app.get('/v1/executions?offset=%s&limit=1' % total_count)
        self.assertEqual(resp.status_int, 200)
        self.assertTrue(len(resp.json), 0)

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

    def test_post_delete_duplicate(self):
        """Cancels an execution twice, to ensure that a full execution object
           is returned instead of an error message
        """

        post_resp = self._do_post(LIVE_ACTION_1)
        self.assertEqual(post_resp.status_int, 201)

        # Similar to test_post_delete, only twice
        for i in range(2):
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

    def test_post_nonexistent_action(self):
        live_action = copy.deepcopy(LIVE_ACTION_1)
        live_action['action'] = 'mock.foobar'
        post_resp = self._do_post(live_action, expect_errors=True)
        self.assertEqual(post_resp.status_int, 400)
        expected_error = 'Action "%s" cannot be found.' % live_action['action']
        self.assertEqual(expected_error, post_resp.json['faultstring'])

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
        self.assertIn('Value "1000" must either be a string or None. Got "int"',
                      post_resp.json['faultstring'])

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
                         'Dependency unsatisfied in variable "ABSENT"')

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
            'pack': 'sixpack',
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
        re_run_resp = self.app.post_json('/v1/executions/%s/re_run' % (execution_id), data)
        self.assertEqual(re_run_resp.status_int, 201)

        # Re-run created execution (with parameters overrides)
        data = {'parameters': {'a': 'val1'}}
        re_run_resp = self.app.post_json('/v1/executions/%s/re_run' % (execution_id), data)
        self.assertEqual(re_run_resp.status_int, 201)

    def test_re_run_with_delay(self):
        post_resp = self._do_post(LIVE_ACTION_1)
        self.assertEqual(post_resp.status_int, 201)
        execution_id = self._get_actionexecution_id(post_resp)

        delay_time = 100
        data = {'delay': delay_time}
        re_run_resp = self.app.post_json('/v1/executions/%s/re_run' % (execution_id), data)
        self.assertEqual(re_run_resp.status_int, 201)
        resp = json.loads(re_run_resp.body)
        self.assertEqual(resp['delay'], delay_time)

    def test_re_run_with_incorrect_delay(self):
        post_resp = self._do_post(LIVE_ACTION_1)
        self.assertEqual(post_resp.status_int, 201)
        execution_id = self._get_actionexecution_id(post_resp)

        delay_time = 'sudo apt -y upgrade winson'
        data = {'delay': delay_time}
        re_run_resp = self.app.post_json('/v1/executions/%s/re_run' % (execution_id),
                                         data, expect_errors=True)
        self.assertEqual(re_run_resp.status_int, 400)

    def test_re_run_with_very_large_delay(self):
        post_resp = self._do_post(LIVE_ACTION_1)
        self.assertEqual(post_resp.status_int, 201)
        execution_id = self._get_actionexecution_id(post_resp)

        delay_time = 10 ** 10
        data = {'delay': delay_time}
        re_run_resp = self.app.post_json('/v1/executions/%s/re_run' % (execution_id), data)
        self.assertEqual(re_run_resp.status_int, 201)

    def test_re_run_delayed_aciton_with_no_delay(self):
        post_resp = self._do_post(LIVE_ACTION_DELAY)
        self.assertEqual(post_resp.status_int, 201)
        execution_id = self._get_actionexecution_id(post_resp)

        delay_time = 0
        data = {'delay': delay_time}
        re_run_resp = self.app.post_json('/v1/executions/%s/re_run' % (execution_id), data)
        self.assertEqual(re_run_resp.status_int, 201)
        resp = json.loads(re_run_resp.body)
        self.assertNotIn('delay', resp.keys())

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
        self.assertIn('Value "1000" must either be a string or None. Got "int"',
                      re_run_resp.json['faultstring'])

    def test_template_param(self):

        # Test with default value containing template
        post_resp = self._do_post(LIVE_ACTION_DEFAULT_TEMPLATE)
        self.assertEqual(post_resp.status_int, 201)

        # Assert that the template in the parameter default value
        # was rendered and st2kv was used
        self.assertEqual(post_resp.json['parameters']['intparam'], 0)

        # Test with live param
        live_int_param = 3
        livaction_with_params = copy.deepcopy(LIVE_ACTION_DEFAULT_TEMPLATE)
        livaction_with_params['parameters'] = {
            "intparam": live_int_param
        }
        post_resp = self._do_post(livaction_with_params)
        self.assertEqual(post_resp.status_int, 201)

        # Assert that the template in the parameter default value
        # was not rendered, and the provided parameter was used
        self.assertEqual(post_resp.json['parameters']['intparam'], live_int_param)

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
            'pack': 'starterpack',
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
            'pack': 'starterpack',
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
            'pack': 'starterpack',
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
            'pack': 'starterpack',
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

    def test_re_run_secret_parameter(self):
        # Create a new execution
        post_resp = self._do_post(LIVE_ACTION_1)
        self.assertEqual(post_resp.status_int, 201)
        execution_id = self._get_actionexecution_id(post_resp)

        # Re-run created execution (no parameters overrides)
        data = {}
        re_run_resp = self.app.post_json('/v1/executions/%s/re_run' % (execution_id), data)
        self.assertEqual(re_run_resp.status_int, 201)

        execution_id = self._get_actionexecution_id(re_run_resp)
        re_run_result = self._do_get_one(execution_id,
                                         params={'show_secrets': True},
                                         expect_errors=True)
        self.assertEqual(re_run_result.json['parameters'], LIVE_ACTION_1['parameters'])

        # Re-run created execution (with parameters overrides)
        data = {'parameters': {'a': 'val1', 'd': ANOTHER_SUPER_SECRET_PARAMETER}}
        re_run_resp = self.app.post_json('/v1/executions/%s/re_run' % (execution_id), data)
        self.assertEqual(re_run_resp.status_int, 201)

        execution_id = self._get_actionexecution_id(re_run_resp)
        re_run_result = self._do_get_one(execution_id,
                                         params={'show_secrets': True},
                                         expect_errors=True)
        self.assertEqual(re_run_result.json['parameters']['d'], data['parameters']['d'])

    def test_put_status_and_result(self):
        post_resp = self._do_post(LIVE_ACTION_1)
        self.assertEqual(post_resp.status_int, 201)

        execution_id = self._get_actionexecution_id(post_resp)
        updates = {'status': 'succeeded', 'result': {'stdout': 'foobar'}}
        put_resp = self._do_put(execution_id, updates)
        self.assertEqual(put_resp.status_int, 200)
        self.assertEqual(put_resp.json['status'], 'succeeded')
        self.assertDictEqual(put_resp.json['result'], {'stdout': 'foobar'})

        get_resp = self._do_get_one(execution_id)
        self.assertEqual(get_resp.status_int, 200)
        self.assertEqual(get_resp.json['status'], 'succeeded')
        self.assertDictEqual(get_resp.json['result'], {'stdout': 'foobar'})

    def test_put_bad_state(self):
        post_resp = self._do_post(LIVE_ACTION_1)
        self.assertEqual(post_resp.status_int, 201)

        execution_id = self._get_actionexecution_id(post_resp)
        updates = {'status': 'married'}
        put_resp = self._do_put(execution_id, updates, expect_errors=True)
        self.assertEqual(put_resp.status_int, 400)
        self.assertIn('\'married\' is not one of', put_resp.json['faultstring'])

    def test_put_bad_result(self):
        post_resp = self._do_post(LIVE_ACTION_1)
        self.assertEqual(post_resp.status_int, 201)

        execution_id = self._get_actionexecution_id(post_resp)
        updates = {'result': 'foobar'}
        put_resp = self._do_put(execution_id, updates, expect_errors=True)
        self.assertEqual(put_resp.status_int, 400)
        self.assertIn('is not of type \'object\'', put_resp.json['faultstring'])

    def test_put_bad_property(self):
        post_resp = self._do_post(LIVE_ACTION_1)
        self.assertEqual(post_resp.status_int, 201)

        execution_id = self._get_actionexecution_id(post_resp)
        updates = {'status': 'abandoned', 'foo': 'bar'}
        put_resp = self._do_put(execution_id, updates, expect_errors=True)
        self.assertEqual(put_resp.status_int, 400)
        self.assertIn('Additional properties are not allowed', put_resp.json['faultstring'])

    def test_put_status_to_completed_execution(self):
        post_resp = self._do_post(LIVE_ACTION_1)
        self.assertEqual(post_resp.status_int, 201)

        execution_id = self._get_actionexecution_id(post_resp)
        updates = {'status': 'succeeded', 'result': {'stdout': 'foobar'}}
        put_resp = self._do_put(execution_id, updates)
        self.assertEqual(put_resp.status_int, 200)
        self.assertEqual(put_resp.json['status'], 'succeeded')
        self.assertDictEqual(put_resp.json['result'], {'stdout': 'foobar'})

        updates = {'status': 'abandoned'}
        put_resp = self._do_put(execution_id, updates, expect_errors=True)
        self.assertEqual(put_resp.status_int, 400)

    @mock.patch.object(
        LiveAction, 'get_by_id',
        mock.MagicMock(return_value=None))
    def test_put_execution_missing_liveaction(self):
        post_resp = self._do_post(LIVE_ACTION_1)
        self.assertEqual(post_resp.status_int, 201)

        execution_id = self._get_actionexecution_id(post_resp)
        updates = {'status': 'succeeded', 'result': {'stdout': 'foobar'}}
        put_resp = self._do_put(execution_id, updates, expect_errors=True)
        self.assertEqual(put_resp.status_int, 500)

    def test_put_pause_unsupported(self):
        post_resp = self._do_post(LIVE_ACTION_1)
        self.assertEqual(post_resp.status_int, 201)

        execution_id = self._get_actionexecution_id(post_resp)

        updates = {'status': 'pausing'}
        put_resp = self._do_put(execution_id, updates, expect_errors=True)
        self.assertEqual(put_resp.status_int, 400)
        self.assertIn('it is not supported', put_resp.json['faultstring'])

        updates = {'status': 'paused'}
        put_resp = self._do_put(execution_id, updates, expect_errors=True)
        self.assertEqual(put_resp.status_int, 400)
        self.assertIn('it is not supported', put_resp.json['faultstring'])

    def test_put_pause(self):
        # Add the runner type to the list of runners that support pause and resume.
        action_constants.WORKFLOW_RUNNER_TYPES.append(ACTION_1['runner_type'])

        try:
            post_resp = self._do_post(LIVE_ACTION_1)
            self.assertEqual(post_resp.status_int, 201)

            execution_id = self._get_actionexecution_id(post_resp)

            updates = {'status': 'running'}
            put_resp = self._do_put(execution_id, updates)
            self.assertEqual(put_resp.status_int, 200)
            self.assertEqual(put_resp.json['status'], 'running')

            updates = {'status': 'pausing'}
            put_resp = self._do_put(execution_id, updates)
            self.assertEqual(put_resp.status_int, 200)
            self.assertEqual(put_resp.json['status'], 'pausing')
            self.assertIsNone(put_resp.json.get('result'))

            get_resp = self._do_get_one(execution_id)
            self.assertEqual(get_resp.status_int, 200)
            self.assertEqual(get_resp.json['status'], 'pausing')
            self.assertIsNone(get_resp.json.get('result'))
        finally:
            action_constants.WORKFLOW_RUNNER_TYPES.remove(ACTION_1['runner_type'])

    def test_put_pause_not_running(self):
        # Add the runner type to the list of runners that support pause and resume.
        action_constants.WORKFLOW_RUNNER_TYPES.append(ACTION_1['runner_type'])

        try:
            post_resp = self._do_post(LIVE_ACTION_1)
            self.assertEqual(post_resp.status_int, 201)
            self.assertEqual(post_resp.json['status'], 'requested')

            execution_id = self._get_actionexecution_id(post_resp)

            updates = {'status': 'pausing'}
            put_resp = self._do_put(execution_id, updates, expect_errors=True)
            self.assertEqual(put_resp.status_int, 400)
            self.assertIn('is not in a running state', put_resp.json['faultstring'])

            get_resp = self._do_get_one(execution_id)
            self.assertEqual(get_resp.status_int, 200)
            self.assertEqual(get_resp.json['status'], 'requested')
            self.assertIsNone(get_resp.json.get('result'))
        finally:
            action_constants.WORKFLOW_RUNNER_TYPES.remove(ACTION_1['runner_type'])

    def test_put_pause_already_pausing(self):
        # Add the runner type to the list of runners that support pause and resume.
        action_constants.WORKFLOW_RUNNER_TYPES.append(ACTION_1['runner_type'])

        try:
            post_resp = self._do_post(LIVE_ACTION_1)
            self.assertEqual(post_resp.status_int, 201)

            execution_id = self._get_actionexecution_id(post_resp)

            updates = {'status': 'running'}
            put_resp = self._do_put(execution_id, updates)
            self.assertEqual(put_resp.status_int, 200)
            self.assertEqual(put_resp.json['status'], 'running')

            updates = {'status': 'pausing'}
            put_resp = self._do_put(execution_id, updates)
            self.assertEqual(put_resp.status_int, 200)
            self.assertEqual(put_resp.json['status'], 'pausing')
            self.assertIsNone(put_resp.json.get('result'))

            with mock.patch.object(action_service, 'update_status', return_value=None) as mocked:
                updates = {'status': 'pausing'}
                put_resp = self._do_put(execution_id, updates)
                self.assertEqual(put_resp.status_int, 200)
                self.assertEqual(put_resp.json['status'], 'pausing')
                mocked.assert_not_called()

            get_resp = self._do_get_one(execution_id)
            self.assertEqual(get_resp.status_int, 200)
            self.assertEqual(get_resp.json['status'], 'pausing')
            self.assertIsNone(get_resp.json.get('result'))
        finally:
            action_constants.WORKFLOW_RUNNER_TYPES.remove(ACTION_1['runner_type'])

    def test_put_resume_unsupported(self):
        post_resp = self._do_post(LIVE_ACTION_1)
        self.assertEqual(post_resp.status_int, 201)

        execution_id = self._get_actionexecution_id(post_resp)
        updates = {'status': 'resuming'}
        put_resp = self._do_put(execution_id, updates, expect_errors=True)
        self.assertEqual(put_resp.status_int, 400)
        self.assertIn('it is not supported', put_resp.json['faultstring'])

    def test_put_resume(self):
        # Add the runner type to the list of runners that support pause and resume.
        action_constants.WORKFLOW_RUNNER_TYPES.append(ACTION_1['runner_type'])

        try:
            post_resp = self._do_post(LIVE_ACTION_1)
            self.assertEqual(post_resp.status_int, 201)

            execution_id = self._get_actionexecution_id(post_resp)

            updates = {'status': 'running'}
            put_resp = self._do_put(execution_id, updates)
            self.assertEqual(put_resp.status_int, 200)
            self.assertEqual(put_resp.json['status'], 'running')

            updates = {'status': 'pausing'}
            put_resp = self._do_put(execution_id, updates)
            self.assertEqual(put_resp.status_int, 200)
            self.assertEqual(put_resp.json['status'], 'pausing')
            self.assertIsNone(put_resp.json.get('result'))

            # Manually change the status to paused because only the runner pause method should
            # set the paused status directly to the liveaction and execution database objects.
            liveaction_id = self._get_liveaction_id(post_resp)
            liveaction = action_db_util.get_liveaction_by_id(liveaction_id)
            action_service.update_status(liveaction, action_constants.LIVEACTION_STATUS_PAUSED)

            get_resp = self._do_get_one(execution_id)
            self.assertEqual(get_resp.status_int, 200)
            self.assertEqual(get_resp.json['status'], 'paused')
            self.assertIsNone(get_resp.json.get('result'))

            updates = {'status': 'resuming'}
            put_resp = self._do_put(execution_id, updates)
            self.assertEqual(put_resp.status_int, 200)
            self.assertEqual(put_resp.json['status'], 'resuming')
            self.assertIsNone(put_resp.json.get('result'))

            get_resp = self._do_get_one(execution_id)
            self.assertEqual(get_resp.status_int, 200)
            self.assertEqual(get_resp.json['status'], 'resuming')
            self.assertIsNone(get_resp.json.get('result'))
        finally:
            action_constants.WORKFLOW_RUNNER_TYPES.remove(ACTION_1['runner_type'])

    def test_put_resume_not_paused(self):
        # Add the runner type to the list of runners that support pause and resume.
        action_constants.WORKFLOW_RUNNER_TYPES.append(ACTION_1['runner_type'])

        try:
            post_resp = self._do_post(LIVE_ACTION_1)
            self.assertEqual(post_resp.status_int, 201)

            execution_id = self._get_actionexecution_id(post_resp)

            updates = {'status': 'running'}
            put_resp = self._do_put(execution_id, updates)
            self.assertEqual(put_resp.status_int, 200)
            self.assertEqual(put_resp.json['status'], 'running')

            updates = {'status': 'pausing'}
            put_resp = self._do_put(execution_id, updates)
            self.assertEqual(put_resp.status_int, 200)
            self.assertEqual(put_resp.json['status'], 'pausing')
            self.assertIsNone(put_resp.json.get('result'))

            updates = {'status': 'resuming'}
            put_resp = self._do_put(execution_id, updates, expect_errors=True)
            self.assertEqual(put_resp.status_int, 400)
            expected_error_message = 'it is in "pausing" state and not in "paused" state'
            self.assertIn(expected_error_message, put_resp.json['faultstring'])

            get_resp = self._do_get_one(execution_id)
            self.assertEqual(get_resp.status_int, 200)
            self.assertEqual(get_resp.json['status'], 'pausing')
            self.assertIsNone(get_resp.json.get('result'))
        finally:
            action_constants.WORKFLOW_RUNNER_TYPES.remove(ACTION_1['runner_type'])

    def test_put_resume_already_running(self):
        # Add the runner type to the list of runners that support pause and resume.
        action_constants.WORKFLOW_RUNNER_TYPES.append(ACTION_1['runner_type'])

        try:
            post_resp = self._do_post(LIVE_ACTION_1)
            self.assertEqual(post_resp.status_int, 201)

            execution_id = self._get_actionexecution_id(post_resp)

            updates = {'status': 'running'}
            put_resp = self._do_put(execution_id, updates)
            self.assertEqual(put_resp.status_int, 200)
            self.assertEqual(put_resp.json['status'], 'running')

            with mock.patch.object(action_service, 'update_status', return_value=None) as mocked:
                updates = {'status': 'resuming'}
                put_resp = self._do_put(execution_id, updates)
                self.assertEqual(put_resp.status_int, 200)
                self.assertEqual(put_resp.json['status'], 'running')
                mocked.assert_not_called()

            get_resp = self._do_get_one(execution_id)
            self.assertEqual(get_resp.status_int, 200)
            self.assertEqual(get_resp.json['status'], 'running')
            self.assertIsNone(get_resp.json.get('result'))
        finally:
            action_constants.WORKFLOW_RUNNER_TYPES.remove(ACTION_1['runner_type'])

    def test_get_inquiry_mask(self):
        """Ensure Inquiry responses are masked when retrieved via ActionExecution GET

        The reason this test is included here is so that we can verify that the ActionExecution
        GET function properly masks fields within an Inquiry response.
        TODO(mierdin): This test, and the constants it uses, should not be necessary here
        once Inquiries get their own data model.
        """

        post_resp = self._do_post(LIVE_ACTION_INQUIRY)
        actionexecution_id = self._get_actionexecution_id(post_resp)
        get_resp = self._do_get_one(actionexecution_id)
        self.assertEqual(get_resp.status_int, 200)

        resp = json.loads(get_resp.body)
        self.assertEqual(resp['result']['response']['secondfactor'], MASKED_ATTRIBUTE_VALUE)

        post_resp = self._do_post(LIVE_ACTION_INQUIRY)
        actionexecution_id = self._get_actionexecution_id(post_resp)
        get_resp = self._do_get_one(actionexecution_id, params={'show_secrets': True})
        self.assertEqual(get_resp.status_int, 200)

        resp = json.loads(get_resp.body)
        self.assertEqual(resp['result']['response']['secondfactor'], "supersecretvalue")

    def test_get_include_attributes_and_secret_parameters(self):
        # Verify that secret parameters are correctly masked when using ?include_attributes filter
        self._do_post(LIVE_ACTION_WITH_SECRET_PARAM)

        urls = [
            '/v1/actionexecutions?include_attributes=parameters',
            '/v1/actionexecutions?include_attributes=parameters,action',
            '/v1/actionexecutions?include_attributes=parameters,runner',
            '/v1/actionexecutions?include_attributes=parameters,action,runner'
        ]

        for url in urls:
            resp = self.app.get(url + '&limit=1')

            self.assertTrue('parameters' in resp.json[0])
            self.assertEqual(resp.json[0]['parameters']['a'], 'param a')
            self.assertEqual(resp.json[0]['parameters']['d'], MASKED_ATTRIBUTE_VALUE)
            self.assertEqual(resp.json[0]['parameters']['password'], MASKED_ATTRIBUTE_VALUE)
            self.assertEqual(resp.json[0]['parameters']['hosts'], 'localhost')

        # With ?show_secrets=True
        urls = [
            ('/v1/actionexecutions?&include_attributes=parameters'),
            ('/v1/actionexecutions?include_attributes=parameters,action'),
            ('/v1/actionexecutions?include_attributes=parameters,runner'),
            ('/v1/actionexecutions?include_attributes=parameters,action,runner')
        ]

        for url in urls:
            resp = self.app.get(url + '&limit=1&show_secrets=True')

            self.assertTrue('parameters' in resp.json[0])
            self.assertEqual(resp.json[0]['parameters']['a'], 'param a')
            self.assertEqual(resp.json[0]['parameters']['d'], 'secretpassword1')
            self.assertEqual(resp.json[0]['parameters']['password'], 'secretpassword2')
            self.assertEqual(resp.json[0]['parameters']['hosts'], 'localhost')

        # NOTE: We don't allow exclusion of attributes such as "action" and "runner" because
        # that would break secrets masking
        urls = [
            '/v1/actionexecutions?limit=1&exclude_attributes=action',
            '/v1/actionexecutions?limit=1&exclude_attributes=runner',
            '/v1/actionexecutions?limit=1&exclude_attributes=action,runner',
        ]

        for url in urls:
            resp = self.app.get(url + '&limit=1', expect_errors=True)

            self.assertEqual(resp.status_int, 400)
            self.assertTrue('Invalid or unsupported exclude attribute specified:' in
                            resp.json['faultstring'])

    def test_get_single_attribute_success(self):
        exec_id = self.app.get('/v1/actionexecutions?limit=1').json[0]['id']

        resp = self.app.get('/v1/executions/%s/attribute/status' % (exec_id))
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json, 'requested')

        resp = self.app.get('/v1/executions/%s/attribute/result' % (exec_id))
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json, None)

        resp = self.app.get('/v1/executions/%s/attribute/trigger_instance' % (exec_id))
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json, None)

        data = {}
        data['status'] = action_constants.LIVEACTION_STATUS_SUCCEEDED
        data['result'] = {'foo': 'bar'}

        resp = self.app.put_json('/v1/executions/%s' % (exec_id), data)
        self.assertEqual(resp.status_int, 200)

        resp = self.app.get('/v1/executions/%s/attribute/result' % (exec_id))
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json, data['result'])

    def test_get_single_attribute_failure_invalid_attribute(self):
        exec_id = self.app.get('/v1/actionexecutions?limit=1').json[0]['id']

        resp = self.app.get('/v1/executions/%s/attribute/start_timestamp' % (exec_id),
                            expect_errors=True)
        self.assertEqual(resp.status_int, 400)
        self.assertTrue('Invalid attribute "start_timestamp" specified.' in
                        resp.json['faultstring'])

    def test_get_single_include_attributes_and_secret_parameters(self):
        # Verify that secret parameters are correctly masked when using ?include_attributes filter
        self._do_post(LIVE_ACTION_WITH_SECRET_PARAM)
        exec_id = self.app.get('/v1/actionexecutions?limit=1').json[0]['id']

        # FYI, the response always contains the 'id' parameter
        urls = [
            {
                'url': '/v1/executions/%s?include_attributes=parameters' % (exec_id),
                'expected_parameters': ['id', 'parameters'],
            },
            {
                'url': '/v1/executions/%s?include_attributes=parameters,action' % (exec_id),
                'expected_parameters': ['id', 'parameters', 'action'],
            },
            {
                'url': '/v1/executions/%s?include_attributes=parameters,runner' % (exec_id),
                'expected_parameters': ['id', 'parameters', 'runner'],
            },
            {
                'url': '/v1/executions/%s?include_attributes=parameters,action,runner' % (exec_id),
                'expected_parameters': ['id', 'parameters', 'action', 'runner'],
            }
        ]

        for item in urls:
            url = item['url']
            resp = self.app.get(url)

            self.assertTrue('parameters' in resp.json)
            self.assertEqual(resp.json['parameters']['a'], 'param a')
            self.assertEqual(resp.json['parameters']['d'], MASKED_ATTRIBUTE_VALUE)
            self.assertEqual(resp.json['parameters']['password'], MASKED_ATTRIBUTE_VALUE)
            self.assertEqual(resp.json['parameters']['hosts'], 'localhost')

            # ensure that the response has only the keys we epect, no more, no less
            resp_keys = set(resp.json.keys())
            expected_params = set(item['expected_parameters'])
            diff = resp_keys.symmetric_difference(expected_params)
            self.assertEqual(diff, set())

        # With ?show_secrets=True
        urls = [
            {
                'url': '/v1/executions/%s?&include_attributes=parameters' % (exec_id),
                'expected_parameters': ['id', 'parameters'],
            },
            {
                'url': '/v1/executions/%s?include_attributes=parameters,action' % (exec_id),
                'expected_parameters': ['id', 'parameters', 'action'],
            },
            {
                'url': '/v1/executions/%s?include_attributes=parameters,runner' % (exec_id),
                'expected_parameters': ['id', 'parameters', 'runner'],
            },
            {
                'url': '/v1/executions/%s?include_attributes=parameters,action,runner' % (exec_id),
                'expected_parameters': ['id', 'parameters', 'action', 'runner'],
            },
        ]

        for item in urls:
            url = item['url']
            resp = self.app.get(url + '&show_secrets=True')

            self.assertTrue('parameters' in resp.json)
            self.assertEqual(resp.json['parameters']['a'], 'param a')
            self.assertEqual(resp.json['parameters']['d'], 'secretpassword1')
            self.assertEqual(resp.json['parameters']['password'], 'secretpassword2')
            self.assertEqual(resp.json['parameters']['hosts'], 'localhost')

            # ensure that the response has only the keys we epect, no more, no less
            resp_keys = set(resp.json.keys())
            expected_params = set(item['expected_parameters'])
            diff = resp_keys.symmetric_difference(expected_params)
            self.assertEqual(diff, set())

        # NOTE: We don't allow exclusion of attributes such as "action" and "runner" because
        # that would break secrets masking
        urls = [
            '/v1/executions/%s?limit=1&exclude_attributes=action',
            '/v1/executions/%s?limit=1&exclude_attributes=runner',
            '/v1/executions/%s?limit=1&exclude_attributes=action,runner',
        ]

        for url in urls:
            resp = self.app.get(url, expect_errors=True)

            self.assertEqual(resp.status_int, 400)
            self.assertTrue('Invalid or unsupported exclude attribute specified:' in
                            resp.json['faultstring'])

    def _insert_mock_models(self):
        execution_1_id = self._get_actionexecution_id(self._do_post(LIVE_ACTION_1))
        execution_2_id = self._get_actionexecution_id(self._do_post(LIVE_ACTION_2))
        return [execution_1_id, execution_2_id]


class ActionExecutionOutputControllerTestCase(BaseActionExecutionControllerTestCase,
                                              FunctionalTest):
    def test_get_output_id_last_no_executions_in_the_database(self):
        ActionExecution.query().delete()

        resp = self.app.get('/v1/executions/last/output', expect_errors=True)
        self.assertEqual(resp.status_int, http_client.BAD_REQUEST)
        self.assertEqual(resp.json['faultstring'], 'No executions found in the database')

    def test_get_output_running_execution(self):
        # Only the output produced so far should be returned
        # Test the execution output API endpoint for execution which is running (blocking)
        status = action_constants.LIVEACTION_STATUS_RUNNING
        timestamp = date_utils.get_datetime_utc_now()
        action_execution_db = ActionExecutionDB(start_timestamp=timestamp,
                                                end_timestamp=timestamp,
                                                status=status,
                                                action={'ref': 'core.local'},
                                                runner={'name': 'local-shell-cmd'},
                                                liveaction={'ref': 'foo'})
        action_execution_db = ActionExecution.add_or_update(action_execution_db)

        output_params = dict(execution_id=str(action_execution_db.id),
                             action_ref='core.local',
                             runner_ref='dummy',
                             timestamp=timestamp,
                             output_type='stdout',
                             data='stdout before start\n')

        def insert_mock_data(data):
            output_params['data'] = data
            output_db = ActionExecutionOutputDB(**output_params)
            ActionExecutionOutput.add_or_update(output_db)

        # Insert mock output object
        output_db = ActionExecutionOutputDB(**output_params)
        ActionExecutionOutput.add_or_update(output_db, publish=False)

        # Retrieve data while execution is running - data produced so far should be retrieved
        resp = self.app.get('/v1/executions/%s/output' % (str(action_execution_db.id)),
                            expect_errors=False)
        self.assertEqual(resp.status_int, 200)
        lines = resp.text.strip().split('\n')
        lines = [line for line in lines if line.strip()]
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0], 'stdout before start')

        # Insert more data
        insert_mock_data('stdout mid 1\n')

        # Retrieve data while execution is running - data produced so far should be retrieved
        resp = self.app.get('/v1/executions/%s/output' % (str(action_execution_db.id)),
                            expect_errors=False)
        self.assertEqual(resp.status_int, 200)
        lines = resp.text.strip().split('\n')
        lines = [line for line in lines if line.strip()]
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], 'stdout before start')
        self.assertEqual(lines[1], 'stdout mid 1')

        # Insert more data
        insert_mock_data('stdout pre finish 1\n')

        # Transition execution to completed state
        action_execution_db.status = action_constants.LIVEACTION_STATUS_SUCCEEDED
        action_execution_db = ActionExecution.add_or_update(action_execution_db)

        # Execution has finished
        resp = self.app.get('/v1/executions/%s/output' % (str(action_execution_db.id)),
                            expect_errors=False)

        self.assertEqual(resp.status_int, 200)
        lines = resp.text.strip().split('\n')
        lines = [line for line in lines if line.strip()]
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0], 'stdout before start')
        self.assertEqual(lines[1], 'stdout mid 1')
        self.assertEqual(lines[2], 'stdout pre finish 1')

    def test_get_output_finished_execution(self):
        # Test the execution output API endpoint for execution which has finished
        for status in action_constants.LIVEACTION_COMPLETED_STATES:
            # Insert mock execution and output objects
            status = action_constants.LIVEACTION_STATUS_SUCCEEDED
            timestamp = date_utils.get_datetime_utc_now()
            action_execution_db = ActionExecutionDB(start_timestamp=timestamp,
                                                    end_timestamp=timestamp,
                                                    status=status,
                                                    action={'ref': 'core.local'},
                                                    runner={'name': 'local-shell-cmd'},
                                                    liveaction={'ref': 'foo'})
            action_execution_db = ActionExecution.add_or_update(action_execution_db)

            for i in range(1, 6):
                stdout_db = ActionExecutionOutputDB(execution_id=str(action_execution_db.id),
                                                    action_ref='core.local',
                                                    runner_ref='dummy',
                                                    timestamp=timestamp,
                                                    output_type='stdout',
                                                    data='stdout %s\n' % (i))
                ActionExecutionOutput.add_or_update(stdout_db)

            for i in range(10, 15):
                stderr_db = ActionExecutionOutputDB(execution_id=str(action_execution_db.id),
                                                    action_ref='core.local',
                                                    runner_ref='dummy',
                                                    timestamp=timestamp,
                                                    output_type='stderr',
                                                    data='stderr %s\n' % (i))
                ActionExecutionOutput.add_or_update(stderr_db)

            resp = self.app.get('/v1/executions/%s/output' % (str(action_execution_db.id)),
                                expect_errors=False)
            self.assertEqual(resp.status_int, 200)
            lines = resp.text.strip().split('\n')
            self.assertEqual(len(lines), 10)
            self.assertEqual(lines[0], 'stdout 1')
            self.assertEqual(lines[9], 'stderr 14')

            # Verify "last" short-hand id works
            resp = self.app.get('/v1/executions/last/output', expect_errors=False)
            self.assertEqual(resp.status_int, 200)
            lines = resp.text.strip().split('\n')
            self.assertEqual(len(lines), 10)
