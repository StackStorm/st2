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

import jsonschema
import mock
import six

from st2actions.container.base import RunnerContainer
from st2common.constants import action as action_constants
from st2common.exceptions.action import InvalidActionParameterException
from st2common.models.db.liveaction import LiveActionDB
from st2common.models.api.action import RunnerTypeAPI, ActionAPI
from st2common.models.system.common import ResourceReference
from st2common.persistence.action import Action
from st2common.persistence.runner import RunnerType
from st2common.services import action as action_service
from st2common.transport.publishers import PoolPublisher
from st2common.util import isotime
from st2common.util import action_db
from st2tests import DbTestCase


RUNNER = {
    'name': 'local-shell-script',
    'description': 'A runner to execute local command.',
    'enabled': True,
    'runner_parameters': {
        'hosts': {'type': 'string'},
        'cmd': {'type': 'string'},
        'sudo': {'type': 'boolean', 'default': False}
    },
    'runner_module': 'st2actions.runners.remoterunner'
}

RUNNER_ACTION_CHAIN = {
    'name': 'action-chain',
    'description': 'AC runner.',
    'enabled': True,
    'runner_parameters': {
    },
    'runner_module': 'st2actions.runners.remoterunner'
}

ACTION = {
    'name': 'my.action',
    'description': 'my test',
    'enabled': True,
    'entry_point': '/tmp/test/action.sh',
    'pack': 'default',
    'runner_type': 'local-shell-script',
    'parameters': {
        'arg_default_value': {
            'type': 'string',
            'default': 'abc'
        },
        'arg_default_type': {
        }
    },
    'notify': {
        'on-complete': {
            'message': 'My awesome action is complete. Party time!!!',
            'routes': ['notify.slack']
        }
    }
}

ACTION_WORKFLOW = {
    'name': 'my.wf_action',
    'description': 'my test',
    'enabled': True,
    'entry_point': '/tmp/test/action.sh',
    'pack': 'default',
    'runner_type': 'action-chain'
}

ACTION_OVR_PARAM = {
    'name': 'my.sudo.default.action',
    'description': 'my test',
    'enabled': True,
    'entry_point': '/tmp/test/action.sh',
    'pack': 'default',
    'runner_type': 'local-shell-script',
    'parameters': {
        'sudo': {
            'default': True
        }
    }
}

ACTION_OVR_PARAM_MUTABLE = {
    'name': 'my.sudo.mutable.action',
    'description': 'my test',
    'enabled': True,
    'entry_point': '/tmp/test/action.sh',
    'pack': 'default',
    'runner_type': 'local-shell-script',
    'parameters': {
        'sudo': {
            'immutable': False
        }
    }
}

ACTION_OVR_PARAM_IMMUTABLE = {
    'name': 'my.sudo.immutable.action',
    'description': 'my test',
    'enabled': True,
    'entry_point': '/tmp/test/action.sh',
    'pack': 'default',
    'runner_type': 'local-shell-script',
    'parameters': {
        'sudo': {
            'immutable': True
        }
    }
}

ACTION_OVR_PARAM_BAD_ATTR = {
    'name': 'my.sudo.invalid.action',
    'description': 'my test',
    'enabled': True,
    'entry_point': '/tmp/test/action.sh',
    'pack': 'default',
    'runner_type': 'local-shell-script',
    'parameters': {
        'sudo': {
            'type': 'number'
        }
    }
}

ACTION_OVR_PARAM_BAD_ATTR_NOOP = {
    'name': 'my.sudo.invalid.noop.action',
    'description': 'my test',
    'enabled': True,
    'entry_point': '/tmp/test/action.sh',
    'pack': 'default',
    'runner_type': 'local-shell-script',
    'parameters': {
        'sudo': {
            'type': 'boolean'
        }
    }
}

PACK = 'default'
ACTION_REF = ResourceReference(name='my.action', pack=PACK).ref
ACTION_WORKFLOW_REF = ResourceReference(name='my.wf_action', pack=PACK).ref
ACTION_OVR_PARAM_REF = ResourceReference(name='my.sudo.default.action', pack=PACK).ref
ACTION_OVR_PARAM_MUTABLE_REF = ResourceReference(name='my.sudo.mutable.action', pack=PACK).ref
ACTION_OVR_PARAM_IMMUTABLE_REF = ResourceReference(name='my.sudo.immutable.action', pack=PACK).ref
ACTION_OVR_PARAM_BAD_ATTR_REF = ResourceReference(name='my.sudo.invalid.action', pack=PACK).ref
ACTION_OVR_PARAM_BAD_ATTR_NOOP_REF = ResourceReference(
    name='my.sudo.invalid.noop.action', pack=PACK).ref

USERNAME = 'stanley'


@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
class TestActionExecutionService(DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestActionExecutionService, cls).setUpClass()
        cls.runner = RunnerTypeAPI(**RUNNER)
        cls.runnerdb = RunnerType.add_or_update(RunnerTypeAPI.to_model(cls.runner))

        runner_api = RunnerTypeAPI(**RUNNER_ACTION_CHAIN)
        RunnerType.add_or_update(RunnerTypeAPI.to_model(runner_api))

        cls.actions = {
            ACTION['name']: ActionAPI(**ACTION),
            ACTION_WORKFLOW['name']: ActionAPI(**ACTION_WORKFLOW),
            ACTION_OVR_PARAM['name']: ActionAPI(**ACTION_OVR_PARAM),
            ACTION_OVR_PARAM_MUTABLE['name']: ActionAPI(**ACTION_OVR_PARAM_MUTABLE),
            ACTION_OVR_PARAM_IMMUTABLE['name']: ActionAPI(**ACTION_OVR_PARAM_IMMUTABLE),
            ACTION_OVR_PARAM_BAD_ATTR['name']: ActionAPI(**ACTION_OVR_PARAM_BAD_ATTR),
            ACTION_OVR_PARAM_BAD_ATTR_NOOP['name']: ActionAPI(**ACTION_OVR_PARAM_BAD_ATTR_NOOP)
        }

        cls.actiondbs = {name: Action.add_or_update(ActionAPI.to_model(action))
                         for name, action in six.iteritems(cls.actions)}

        cls.container = RunnerContainer()

    @classmethod
    def tearDownClass(cls):
        for actiondb in cls.actiondbs.values():
            Action.delete(actiondb)

        RunnerType.delete(cls.runnerdb)

        super(TestActionExecutionService, cls).tearDownClass()

    def _submit_request(self, action_ref=ACTION_REF):
        context = {'user': USERNAME}
        parameters = {'hosts': '127.0.0.1', 'cmd': 'uname -a'}
        request = LiveActionDB(action=action_ref, context=context, parameters=parameters)
        request, _ = action_service.request(request)
        execution = action_db.get_liveaction_by_id(str(request.id))
        return request, execution

    def _submit_cancellation(self, execution):
        execution, _ = action_service.request_cancellation(execution, USERNAME)
        execution = action_db.get_liveaction_by_id(execution.id)
        return execution

    def test_request_non_workflow_action(self):
        actiondb = self.actiondbs[ACTION['name']]
        request, execution = self._submit_request(action_ref=ACTION_REF)

        self.assertIsNotNone(execution)
        self.assertEqual(execution.action_is_workflow, False)
        self.assertEqual(execution.id, request.id)
        self.assertEqual(execution.action, '.'.join([actiondb.pack, actiondb.name]))
        self.assertEqual(execution.context['user'], request.context['user'])
        self.assertDictEqual(execution.parameters, request.parameters)
        self.assertEqual(execution.status, action_constants.LIVEACTION_STATUS_REQUESTED)
        self.assertTrue(execution.notify is not None)
        # mongoengine DateTimeField stores datetime only up to milliseconds
        self.assertEqual(isotime.format(execution.start_timestamp, usec=False),
                         isotime.format(request.start_timestamp, usec=False))

    def test_request_workflow_action(self):
        actiondb = self.actiondbs[ACTION_WORKFLOW['name']]
        request, execution = self._submit_request(action_ref=ACTION_WORKFLOW_REF)

        self.assertIsNotNone(execution)
        self.assertEqual(execution.action_is_workflow, True)
        self.assertEqual(execution.id, request.id)
        self.assertEqual(execution.action, '.'.join([actiondb.pack, actiondb.name]))
        self.assertEqual(execution.context['user'], request.context['user'])
        self.assertDictEqual(execution.parameters, request.parameters)
        self.assertEqual(execution.status, action_constants.LIVEACTION_STATUS_REQUESTED)

    def test_request_invalid_parameters(self):
        parameters = {'hosts': '127.0.0.1', 'cmd': 'uname -a', 'arg_default_value': 123}
        liveaction = LiveActionDB(action=ACTION_REF, parameters=parameters)
        self.assertRaises(jsonschema.ValidationError, action_service.request, liveaction)

    def test_request_optional_parameter_none_value(self):
        parameters = {'hosts': '127.0.0.1', 'cmd': 'uname -a', 'arg_default_value': None}
        request = LiveActionDB(action=ACTION_REF, parameters=parameters)
        request, _ = action_service.request(request)

    def test_request_optional_parameter_none_value_no_default(self):
        parameters = {'hosts': '127.0.0.1', 'cmd': 'uname -a', 'arg_default_type': None}
        request = LiveActionDB(action=ACTION_REF, parameters=parameters)
        request, _ = action_service.request(request)

    def test_request_override_runner_parameter(self):
        parameters = {'hosts': '127.0.0.1', 'cmd': 'uname -a'}
        request = LiveActionDB(action=ACTION_OVR_PARAM_REF, parameters=parameters)
        request, _ = action_service.request(request)

        parameters = {'hosts': '127.0.0.1', 'cmd': 'uname -a', 'sudo': False}
        request = LiveActionDB(action=ACTION_OVR_PARAM_REF, parameters=parameters)
        request, _ = action_service.request(request)

    def test_request_override_runner_parameter_type_attribute_value_changed(self):
        parameters = {'hosts': '127.0.0.1', 'cmd': 'uname -a'}
        request = LiveActionDB(action=ACTION_OVR_PARAM_BAD_ATTR_REF, parameters=parameters)

        with self.assertRaises(InvalidActionParameterException) as ex_ctx:
            request, _ = action_service.request(request)

        expected = ('The attribute "type" for the runner parameter "sudo" in '
                    'action "default.my.sudo.invalid.action" cannot be overridden.')
        self.assertEqual(str(ex_ctx.exception), expected)

    def test_request_override_runner_parameter_type_attribute_no_value_changed(self):
        parameters = {'hosts': '127.0.0.1', 'cmd': 'uname -a'}
        request = LiveActionDB(action=ACTION_OVR_PARAM_BAD_ATTR_NOOP_REF, parameters=parameters)
        request, _ = action_service.request(request)

    def test_request_override_runner_parameter_mutable(self):
        parameters = {'hosts': '127.0.0.1', 'cmd': 'uname -a'}
        request = LiveActionDB(action=ACTION_OVR_PARAM_MUTABLE_REF, parameters=parameters)
        request, _ = action_service.request(request)

        parameters = {'hosts': '127.0.0.1', 'cmd': 'uname -a', 'sudo': True}
        request = LiveActionDB(action=ACTION_OVR_PARAM_MUTABLE_REF, parameters=parameters)
        request, _ = action_service.request(request)

    def test_request_override_runner_parameter_immutable(self):
        parameters = {'hosts': '127.0.0.1', 'cmd': 'uname -a'}
        request = LiveActionDB(action=ACTION_OVR_PARAM_IMMUTABLE_REF, parameters=parameters)
        request, _ = action_service.request(request)

        parameters = {'hosts': '127.0.0.1', 'cmd': 'uname -a', 'sudo': True}
        request = LiveActionDB(action=ACTION_OVR_PARAM_IMMUTABLE_REF, parameters=parameters)
        self.assertRaises(ValueError, action_service.request, request)

    def test_request_nonexistent_action(self):
        parameters = {'hosts': '127.0.0.1', 'cmd': 'uname -a'}
        action_ref = ResourceReference(name='i.action', pack='default').ref
        execution = LiveActionDB(action=action_ref, parameters=parameters)
        self.assertRaises(ValueError, action_service.request, execution)

    def test_request_disabled_action(self):
        actiondb = self.actiondbs[ACTION['name']]
        actiondb.enabled = False
        Action.add_or_update(actiondb)

        try:
            parameters = {'hosts': '127.0.0.1', 'cmd': 'uname -a'}
            execution = LiveActionDB(action=ACTION_REF, parameters=parameters)
            self.assertRaises(ValueError, action_service.request, execution)
        except Exception as e:
            raise e
        finally:
            actiondb.enabled = True
            Action.add_or_update(actiondb)

    def test_request_cancellation(self):
        request, execution = self._submit_request()
        self.assertIsNotNone(execution)
        self.assertEqual(execution.id, request.id)
        self.assertEqual(execution.status, action_constants.LIVEACTION_STATUS_REQUESTED)

        # Update execution status to RUNNING.
        action_service.update_status(execution, action_constants.LIVEACTION_STATUS_RUNNING, False)
        execution = action_db.get_liveaction_by_id(execution.id)
        self.assertEqual(execution.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Request cancellation.
        execution = self._submit_cancellation(execution)
        self.assertEqual(execution.status, action_constants.LIVEACTION_STATUS_CANCELING)

    def test_request_cancellation_uncancelable_state(self):
        request, execution = self._submit_request()
        self.assertIsNotNone(execution)
        self.assertEqual(execution.id, request.id)
        self.assertEqual(execution.status, action_constants.LIVEACTION_STATUS_REQUESTED)

        # Update execution status to FAILED.
        action_service.update_status(execution, action_constants.LIVEACTION_STATUS_FAILED, False)
        execution = action_db.get_liveaction_by_id(execution.id)
        self.assertEqual(execution.status, action_constants.LIVEACTION_STATUS_FAILED)

        # Request cancellation.
        self.assertRaises(Exception, action_service.request_cancellation, execution)

    def test_request_cancellation_on_idle_execution(self):
        request, execution = self._submit_request()
        self.assertIsNotNone(execution)
        self.assertEqual(execution.id, request.id)
        self.assertEqual(execution.status, action_constants.LIVEACTION_STATUS_REQUESTED)

        # Request cancellation.
        execution = self._submit_cancellation(execution)
        self.assertEqual(execution.status, action_constants.LIVEACTION_STATUS_CANCELED)
