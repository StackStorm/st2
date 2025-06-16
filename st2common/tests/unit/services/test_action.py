# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
import jsonschema
import mock
import six

from st2actions.container.base import RunnerContainer
from st2common.constants import action as action_constants
from st2common.exceptions import action as action_exc
from st2common.exceptions import actionrunner as runner_exc
from st2common.models.db.liveaction import LiveActionDB
from st2common.models.api.action import RunnerTypeAPI, ActionAPI
from st2common.models.system.common import ResourceReference
from st2common.persistence.action import Action
from st2common.persistence.liveaction import LiveAction
from st2common.persistence.runner import RunnerType
from st2common.runners import utils as runners_utils
from st2common.services import action as action_service
from st2common.services import executions
from st2common.transport.publishers import PoolPublisher
from st2common.util import isotime
from st2common.util import action_db
from st2tests import DbTestCase
from six.moves import range


RUNNER = {
    "name": "local-shell-script",
    "description": "A runner to execute local command.",
    "enabled": True,
    "runner_parameters": {
        "hosts": {"type": "string"},
        "cmd": {"type": "string"},
        "sudo": {"type": "boolean", "default": False},
    },
    "runner_module": "remoterunner",
}

RUNNER_ACTION_CHAIN = {
    "name": "action-chain",
    "description": "AC runner.",
    "enabled": True,
    "runner_parameters": {},
    "runner_module": "remoterunner",
}

ACTION = {
    "name": "my.action",
    "description": "my test",
    "enabled": True,
    "entry_point": "/tmp/test/action.sh",
    "pack": "default",
    "runner_type": "local-shell-script",
    "parameters": {
        "arg_default_value": {"type": "string", "default": "abc"},
        "arg_default_type": {},
    },
    "notify": {
        "on-complete": {
            "message": "My awesome action is complete. Party time!!!",
            "routes": ["notify.slack"],
        }
    },
}

ACTION_WORKFLOW = {
    "name": "my.wf_action",
    "description": "my test",
    "enabled": True,
    "entry_point": "/tmp/test/action.sh",
    "pack": "default",
    "runner_type": "action-chain",
}

ACTION_OVR_PARAM = {
    "name": "my.sudo.default.action",
    "description": "my test",
    "enabled": True,
    "entry_point": "/tmp/test/action.sh",
    "pack": "default",
    "runner_type": "local-shell-script",
    "parameters": {"sudo": {"default": True}},
}

ACTION_OVR_PARAM_MUTABLE = {
    "name": "my.sudo.mutable.action",
    "description": "my test",
    "enabled": True,
    "entry_point": "/tmp/test/action.sh",
    "pack": "default",
    "runner_type": "local-shell-script",
    "parameters": {"sudo": {"immutable": False}},
}

ACTION_OVR_PARAM_IMMUTABLE = {
    "name": "my.sudo.immutable.action",
    "description": "my test",
    "enabled": True,
    "entry_point": "/tmp/test/action.sh",
    "pack": "default",
    "runner_type": "local-shell-script",
    "parameters": {"sudo": {"immutable": True}},
}

ACTION_OVR_PARAM_BAD_ATTR = {
    "name": "my.sudo.invalid.action",
    "description": "my test",
    "enabled": True,
    "entry_point": "/tmp/test/action.sh",
    "pack": "default",
    "runner_type": "local-shell-script",
    "parameters": {"sudo": {"type": "number"}},
}

ACTION_OVR_PARAM_BAD_ATTR_NOOP = {
    "name": "my.sudo.invalid.noop.action",
    "description": "my test",
    "enabled": True,
    "entry_point": "/tmp/test/action.sh",
    "pack": "default",
    "runner_type": "local-shell-script",
    "parameters": {"sudo": {"type": "boolean"}},
}

PACK = "default"
ACTION_REF = ResourceReference(name="my.action", pack=PACK).ref
ACTION_WORKFLOW_REF = ResourceReference(name="my.wf_action", pack=PACK).ref
ACTION_OVR_PARAM_REF = ResourceReference(name="my.sudo.default.action", pack=PACK).ref
ACTION_OVR_PARAM_MUTABLE_REF = ResourceReference(
    name="my.sudo.mutable.action", pack=PACK
).ref
ACTION_OVR_PARAM_IMMUTABLE_REF = ResourceReference(
    name="my.sudo.immutable.action", pack=PACK
).ref
ACTION_OVR_PARAM_BAD_ATTR_REF = ResourceReference(
    name="my.sudo.invalid.action", pack=PACK
).ref
ACTION_OVR_PARAM_BAD_ATTR_NOOP_REF = ResourceReference(
    name="my.sudo.invalid.noop.action", pack=PACK
).ref

USERNAME = "stanley"


@mock.patch.object(runners_utils, "invoke_post_run", mock.MagicMock(return_value=None))
@mock.patch.object(PoolPublisher, "publish", mock.MagicMock())
class TestActionExecutionService(DbTestCase):
    @classmethod
    def setUpClass(cls):
        super(TestActionExecutionService, cls).setUpClass()
        cls.runner = RunnerTypeAPI(**RUNNER)
        cls.runnerdb = RunnerType.add_or_update(RunnerTypeAPI.to_model(cls.runner))

        runner_api = RunnerTypeAPI(**RUNNER_ACTION_CHAIN)
        RunnerType.add_or_update(RunnerTypeAPI.to_model(runner_api))

        cls.actions = {
            ACTION["name"]: ActionAPI(**ACTION),
            ACTION_WORKFLOW["name"]: ActionAPI(**ACTION_WORKFLOW),
            ACTION_OVR_PARAM["name"]: ActionAPI(**ACTION_OVR_PARAM),
            ACTION_OVR_PARAM_MUTABLE["name"]: ActionAPI(**ACTION_OVR_PARAM_MUTABLE),
            ACTION_OVR_PARAM_IMMUTABLE["name"]: ActionAPI(**ACTION_OVR_PARAM_IMMUTABLE),
            ACTION_OVR_PARAM_BAD_ATTR["name"]: ActionAPI(**ACTION_OVR_PARAM_BAD_ATTR),
            ACTION_OVR_PARAM_BAD_ATTR_NOOP["name"]: ActionAPI(
                **ACTION_OVR_PARAM_BAD_ATTR_NOOP
            ),
        }

        cls.actiondbs = {
            name: Action.add_or_update(ActionAPI.to_model(action))
            for name, action in six.iteritems(cls.actions)
        }

        cls.container = RunnerContainer()

    @classmethod
    def tearDownClass(cls):
        for actiondb in cls.actiondbs.values():
            Action.delete(actiondb)

        RunnerType.delete(cls.runnerdb)

        super(TestActionExecutionService, cls).tearDownClass()

    def _submit_request(self, action_ref=ACTION_REF):
        context = {"user": USERNAME}
        parameters = {"hosts": "127.0.0.1", "cmd": "uname -a"}
        req = LiveActionDB(action=action_ref, context=context, parameters=parameters)
        req, _ = action_service.request(req)
        ex = action_db.get_liveaction_by_id(str(req.id))
        return req, ex

    def _submit_cancellation(self, execution):
        execution, _ = action_service.request_cancellation(execution, USERNAME)
        execution = action_db.get_liveaction_by_id(execution.id)
        return execution

    def _submit_pause(self, execution):
        execution, _ = action_service.request_pause(execution, USERNAME)
        execution = action_db.get_liveaction_by_id(execution.id)
        return execution

    def _submit_resume(self, execution):
        execution, _ = action_service.request_resume(execution, USERNAME)
        execution = action_db.get_liveaction_by_id(execution.id)
        return execution

    def _create_nested_executions(self, depth=2):
        """Utility function for easily creating nested LiveAction and ActionExecutions for testing

        returns (childmost_liveaction_db, parentmost_liveaction_db)
        """

        if depth <= 0:
            raise Exception("Please provide a depth > 0")

        root_liveaction_db = LiveActionDB()
        root_liveaction_db.status = action_constants.LIVEACTION_STATUS_PAUSED
        root_liveaction_db.action = ACTION_WORKFLOW_REF
        root_liveaction_db = LiveAction.add_or_update(root_liveaction_db)
        root_ex = executions.create_execution_object(root_liveaction_db)

        last_id = root_ex["id"]

        # Create children to the specified depth
        for i in range(depth):

            # Childmost liveaction should use ACTION_REF, everything else
            # should use ACTION_WORKFLOW_REF
            if i == depth:
                action = ACTION_REF
            else:
                action = ACTION_WORKFLOW_REF

            child_liveaction_db = LiveActionDB()
            child_liveaction_db.status = action_constants.LIVEACTION_STATUS_PAUSED
            child_liveaction_db.action = action
            child_liveaction_db.context = {"parent": {"execution_id": last_id}}
            child_liveaction_db = LiveAction.add_or_update(child_liveaction_db)
            parent_ex = executions.create_execution_object(child_liveaction_db)
            last_id = parent_ex.id

        # Return the last-created child as well as the root
        return (child_liveaction_db, root_liveaction_db)

    def test_req_non_workflow_action(self):
        actiondb = self.actiondbs[ACTION["name"]]
        req, ex = self._submit_request(action_ref=ACTION_REF)

        self.assertIsNotNone(ex)
        self.assertEqual(ex.action_is_workflow, False)
        self.assertEqual(ex.id, req.id)
        self.assertEqual(ex.action, ".".join([actiondb.pack, actiondb.name]))
        self.assertEqual(ex.context["user"], req.context["user"])
        self.assertDictEqual(ex.parameters, req.parameters)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_REQUESTED)
        self.assertIsNotNone(ex.notify)
        # mongoengine DateTimeField stores datetime only up to milliseconds
        self.assertEqual(
            isotime.format(ex.start_timestamp, usec=False),
            isotime.format(req.start_timestamp, usec=False),
        )

    def test_req_workflow_action(self):
        actiondb = self.actiondbs[ACTION_WORKFLOW["name"]]
        req, ex = self._submit_request(action_ref=ACTION_WORKFLOW_REF)

        self.assertIsNotNone(ex)
        self.assertEqual(ex.action_is_workflow, True)
        self.assertEqual(ex.id, req.id)
        self.assertEqual(ex.action, ".".join([actiondb.pack, actiondb.name]))
        self.assertEqual(ex.context["user"], req.context["user"])
        self.assertDictEqual(ex.parameters, req.parameters)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_REQUESTED)

    def test_req_invalid_parameters(self):
        parameters = {"hosts": "127.0.0.1", "cmd": "uname -a", "arg_default_value": 123}
        liveaction = LiveActionDB(action=ACTION_REF, parameters=parameters)
        self.assertRaises(
            jsonschema.ValidationError, action_service.request, liveaction
        )

    def test_req_optional_parameter_none_value(self):
        parameters = {
            "hosts": "127.0.0.1",
            "cmd": "uname -a",
            "arg_default_value": None,
        }
        req = LiveActionDB(action=ACTION_REF, parameters=parameters)
        req, _ = action_service.request(req)

    def test_req_optional_parameter_none_value_no_default(self):
        parameters = {"hosts": "127.0.0.1", "cmd": "uname -a", "arg_default_type": None}
        req = LiveActionDB(action=ACTION_REF, parameters=parameters)
        req, _ = action_service.request(req)

    def test_req_override_runner_parameter(self):
        parameters = {"hosts": "127.0.0.1", "cmd": "uname -a"}
        req = LiveActionDB(action=ACTION_OVR_PARAM_REF, parameters=parameters)
        req, _ = action_service.request(req)

        parameters = {"hosts": "127.0.0.1", "cmd": "uname -a", "sudo": False}
        req = LiveActionDB(action=ACTION_OVR_PARAM_REF, parameters=parameters)
        req, _ = action_service.request(req)

    def test_req_override_runner_parameter_type_attribute_value_changed(self):
        parameters = {"hosts": "127.0.0.1", "cmd": "uname -a"}
        req = LiveActionDB(action=ACTION_OVR_PARAM_BAD_ATTR_REF, parameters=parameters)

        with self.assertRaises(action_exc.InvalidActionParameterException) as ex_ctx:
            req, _ = action_service.request(req)

        expected = (
            'The attribute "type" for the runner parameter "sudo" in '
            'action "default.my.sudo.invalid.action" cannot be overridden.'
        )
        self.assertEqual(str(ex_ctx.exception), expected)

    def test_req_override_runner_parameter_type_attribute_no_value_changed(self):
        parameters = {"hosts": "127.0.0.1", "cmd": "uname -a"}
        req = LiveActionDB(
            action=ACTION_OVR_PARAM_BAD_ATTR_NOOP_REF, parameters=parameters
        )
        req, _ = action_service.request(req)

    def test_req_override_runner_parameter_mutable(self):
        parameters = {"hosts": "127.0.0.1", "cmd": "uname -a"}
        req = LiveActionDB(action=ACTION_OVR_PARAM_MUTABLE_REF, parameters=parameters)
        req, _ = action_service.request(req)

        parameters = {"hosts": "127.0.0.1", "cmd": "uname -a", "sudo": True}
        req = LiveActionDB(action=ACTION_OVR_PARAM_MUTABLE_REF, parameters=parameters)
        req, _ = action_service.request(req)

    def test_req_override_runner_parameter_immutable(self):
        parameters = {"hosts": "127.0.0.1", "cmd": "uname -a"}
        req = LiveActionDB(action=ACTION_OVR_PARAM_IMMUTABLE_REF, parameters=parameters)
        req, _ = action_service.request(req)

        parameters = {"hosts": "127.0.0.1", "cmd": "uname -a", "sudo": True}
        req = LiveActionDB(action=ACTION_OVR_PARAM_IMMUTABLE_REF, parameters=parameters)
        self.assertRaises(ValueError, action_service.request, req)

    def test_req_nonexistent_action(self):
        parameters = {"hosts": "127.0.0.1", "cmd": "uname -a"}
        action_ref = ResourceReference(name="i.action", pack="default").ref
        ex = LiveActionDB(action=action_ref, parameters=parameters)
        self.assertRaises(ValueError, action_service.request, ex)

    def test_req_disabled_action(self):
        actiondb = self.actiondbs[ACTION["name"]]
        actiondb.enabled = False
        Action.add_or_update(actiondb)

        try:
            parameters = {"hosts": "127.0.0.1", "cmd": "uname -a"}
            ex = LiveActionDB(action=ACTION_REF, parameters=parameters)
            self.assertRaises(ValueError, action_service.request, ex)
        except Exception as e:
            raise e
        finally:
            actiondb.enabled = True
            Action.add_or_update(actiondb)

    def test_req_cancellation(self):
        req, ex = self._submit_request()
        self.assertIsNotNone(ex)
        self.assertEqual(ex.id, req.id)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_REQUESTED)

        # Update ex status to RUNNING.
        action_service.update_status(
            ex, action_constants.LIVEACTION_STATUS_RUNNING, False
        )
        ex = action_db.get_liveaction_by_id(ex.id)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Request cancellation.
        ex = self._submit_cancellation(ex)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_CANCELING)

    def test_req_cancellation_uncancelable_state(self):
        req, ex = self._submit_request()
        self.assertIsNotNone(ex)
        self.assertEqual(ex.id, req.id)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_REQUESTED)

        # Update ex status to FAILED.
        action_service.update_status(
            ex, action_constants.LIVEACTION_STATUS_FAILED, False
        )
        ex = action_db.get_liveaction_by_id(ex.id)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_FAILED)

        # Request cancellation.
        self.assertRaises(Exception, action_service.request_cancellation, ex)

    def test_req_cancellation_on_idle_ex(self):
        req, ex = self._submit_request()
        self.assertIsNotNone(ex)
        self.assertEqual(ex.id, req.id)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_REQUESTED)

        # Request cancellation.
        ex = self._submit_cancellation(ex)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_CANCELED)

    def test_req_pause_unsupported(self):
        req, ex = self._submit_request()
        self.assertIsNotNone(ex)
        self.assertEqual(ex.id, req.id)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_REQUESTED)

        # Update ex status to RUNNING.
        action_service.update_status(
            ex, action_constants.LIVEACTION_STATUS_RUNNING, False
        )
        ex = action_db.get_liveaction_by_id(ex.id)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Request pause.
        self.assertRaises(
            runner_exc.InvalidActionRunnerOperationError, self._submit_pause, ex
        )

    def test_req_pause(self):
        # Add the runner type to the list of runners that support pause and resume.
        action_constants.WORKFLOW_RUNNER_TYPES.append(ACTION["runner_type"])

        try:
            req, ex = self._submit_request()
            self.assertIsNotNone(ex)
            self.assertEqual(ex.id, req.id)
            self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_REQUESTED)

            # Update ex status to RUNNING.
            action_service.update_status(
                ex, action_constants.LIVEACTION_STATUS_RUNNING, False
            )
            ex = action_db.get_liveaction_by_id(ex.id)
            self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_RUNNING)

            # Request pause.
            ex = self._submit_pause(ex)
            self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_PAUSING)
        finally:
            action_constants.WORKFLOW_RUNNER_TYPES.remove(ACTION["runner_type"])

    def test_req_pause_not_running(self):
        # Add the runner type to the list of runners that support pause and resume.
        action_constants.WORKFLOW_RUNNER_TYPES.append(ACTION["runner_type"])

        try:
            req, ex = self._submit_request()
            self.assertIsNotNone(ex)
            self.assertEqual(ex.id, req.id)
            self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_REQUESTED)

            # Request pause.
            self.assertRaises(
                runner_exc.UnexpectedActionExecutionStatusError, self._submit_pause, ex
            )
        finally:
            action_constants.WORKFLOW_RUNNER_TYPES.remove(ACTION["runner_type"])

    def test_req_pause_already_pausing(self):
        # Add the runner type to the list of runners that support pause and resume.
        action_constants.WORKFLOW_RUNNER_TYPES.append(ACTION["runner_type"])

        try:
            req, ex = self._submit_request()
            self.assertIsNotNone(ex)
            self.assertEqual(ex.id, req.id)
            self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_REQUESTED)

            # Update ex status to RUNNING.
            action_service.update_status(
                ex, action_constants.LIVEACTION_STATUS_RUNNING, False
            )
            ex = action_db.get_liveaction_by_id(ex.id)
            self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_RUNNING)

            # Request pause.
            ex = self._submit_pause(ex)
            self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_PAUSING)

            # Request pause again.
            with mock.patch.object(
                action_service, "update_status", return_value=None
            ) as mocked:
                ex = self._submit_pause(ex)
                self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_PAUSING)
                mocked.assert_not_called()
        finally:
            action_constants.WORKFLOW_RUNNER_TYPES.remove(ACTION["runner_type"])

    def test_req_resume_unsupported(self):
        req, ex = self._submit_request()
        self.assertIsNotNone(ex)
        self.assertEqual(ex.id, req.id)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_REQUESTED)

        # Update ex status to RUNNING.
        action_service.update_status(
            ex, action_constants.LIVEACTION_STATUS_RUNNING, False
        )
        ex = action_db.get_liveaction_by_id(ex.id)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Request resume.
        self.assertRaises(
            runner_exc.InvalidActionRunnerOperationError, self._submit_resume, ex
        )

    def test_req_resume(self):
        # Add the runner type to the list of runners that support pause and resume.
        action_constants.WORKFLOW_RUNNER_TYPES.append(ACTION["runner_type"])

        try:
            req, ex = self._submit_request()
            self.assertIsNotNone(ex)
            self.assertEqual(ex.id, req.id)
            self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_REQUESTED)

            # Update ex status to RUNNING.
            action_service.update_status(
                ex, action_constants.LIVEACTION_STATUS_RUNNING, False
            )
            ex = action_db.get_liveaction_by_id(ex.id)
            self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_RUNNING)

            # Request pause.
            ex = self._submit_pause(ex)
            self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_PAUSING)

            # Update ex status to PAUSED.
            action_service.update_status(
                ex, action_constants.LIVEACTION_STATUS_PAUSED, False
            )
            ex = action_db.get_liveaction_by_id(ex.id)
            self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_PAUSED)

            # Request resume.
            ex = self._submit_resume(ex)
            self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_RESUMING)
        finally:
            action_constants.WORKFLOW_RUNNER_TYPES.remove(ACTION["runner_type"])

    def test_req_resume_not_paused(self):
        # Add the runner type to the list of runners that support pause and resume.
        action_constants.WORKFLOW_RUNNER_TYPES.append(ACTION["runner_type"])

        try:
            req, ex = self._submit_request()
            self.assertIsNotNone(ex)
            self.assertEqual(ex.id, req.id)
            self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_REQUESTED)

            # Update ex status to RUNNING.
            action_service.update_status(
                ex, action_constants.LIVEACTION_STATUS_RUNNING, False
            )
            ex = action_db.get_liveaction_by_id(ex.id)
            self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_RUNNING)

            # Request pause.
            ex = self._submit_pause(ex)
            self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_PAUSING)

            # Request resume.
            self.assertRaises(
                runner_exc.UnexpectedActionExecutionStatusError, self._submit_resume, ex
            )
        finally:
            action_constants.WORKFLOW_RUNNER_TYPES.remove(ACTION["runner_type"])

    def test_req_resume_already_running(self):
        # Add the runner type to the list of runners that support pause and resume.
        action_constants.WORKFLOW_RUNNER_TYPES.append(ACTION["runner_type"])

        try:
            req, ex = self._submit_request()
            self.assertIsNotNone(ex)
            self.assertEqual(ex.id, req.id)
            self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_REQUESTED)

            # Update ex status to RUNNING.
            action_service.update_status(
                ex, action_constants.LIVEACTION_STATUS_RUNNING, False
            )
            ex = action_db.get_liveaction_by_id(ex.id)
            self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_RUNNING)

            # Request resume.
            with mock.patch.object(
                action_service, "update_status", return_value=None
            ) as mocked:
                ex = self._submit_resume(ex)
                self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_RUNNING)
                mocked.assert_not_called()
        finally:
            action_constants.WORKFLOW_RUNNER_TYPES.remove(ACTION["runner_type"])

    def test_root_liveaction(self):
        """Test that get_root_liveaction correctly retrieves the root liveaction"""

        # Test a variety of depths
        for i in range(1, 7):

            child, expected_root = self._create_nested_executions(depth=i)
            actual_root = action_service.get_root_liveaction(child)
            self.assertEqual(expected_root["id"], actual_root["id"])

    def test_invalid_json_request_validate(self):
        parameters = {"hosts": "127.0.0.1", "cmd": "uname -a", "arg_default_value": 123}
        liveaction = LiveActionDB(action=ACTION_REF, parameters=parameters)

        self.assertRaisesRegex(
            jsonschema.ValidationError,
            "123 is not of type 'string'",
            action_service.create_request,
            liveaction,
        )

    def test_invalid_json_request_skipvalidate(self):
        parameters = {"hosts": "127.0.0.1", "cmd": "uname -a", "arg_default_value": 123}
        liveaction = LiveActionDB(action=ACTION_REF, parameters=parameters)

        # Validate that if skip validation that no exception raised
        (action, execution) = action_service.create_request(
            liveaction, validate_params=False
        )
        self.assertTrue(action)
        self.assertTrue(execution)
