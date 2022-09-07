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
from orquesta import statuses as wf_statuses

import st2tests

# XXX: actionsensor import depends on config being setup.
import st2tests.config as tests_config

tests_config.parse_args()

from tests.unit import base

from st2actions.notifier import notifier
from st2common.bootstrap import actionsregistrar
from st2common.bootstrap import runnersregistrar
from st2common.constants import action as action_constants
from st2common.models.api import notification as notify_api_models
from st2common.models.db import liveaction as lv_db_models
from st2common.persistence import execution as ex_db_access
from st2common.persistence import liveaction as lv_db_access
from st2common.persistence import workflow as wf_db_access
from st2common.services import action as action_service
from st2common.services import workflows as workflow_service
from st2common.transport import liveaction as lv_ac_xport
from st2common.transport import workflow as wf_ex_xport
from st2common.transport import publishers
from st2tests.fixtures.packs.core.fixture import PACK_PATH as CORE_PACK_PATH
from st2tests.fixtures.packs.orquesta_tests.fixture import PACK_PATH as TEST_PACK_PATH
from st2tests.mocks import execution as mock_ac_ex_xport
from st2tests.mocks import liveaction as mock_lv_ac_xport
from st2tests.mocks import workflow as mock_wf_ex_xport

PACKS = [TEST_PACK_PATH, CORE_PACK_PATH]

MOCK_NOTIFY = {
    "on-complete": {
        "data": {"source_channel": "baloney", "user": "lakstorm"},
        "routes": ["hubot"],
    }
}


@mock.patch.object(
    notifier.Notifier, "_post_notify_triggers", mock.MagicMock(return_value=None)
)
@mock.patch.object(
    notifier.Notifier, "_post_generic_trigger", mock.MagicMock(return_value=None)
)
@mock.patch.object(
    publishers.CUDPublisher,
    "publish_update",
    mock.MagicMock(side_effect=mock_ac_ex_xport.MockExecutionPublisher.publish_update),
)
@mock.patch.object(
    lv_ac_xport.LiveActionPublisher,
    "publish_create",
    mock.MagicMock(side_effect=mock_lv_ac_xport.MockLiveActionPublisher.publish_create),
)
@mock.patch.object(
    lv_ac_xport.LiveActionPublisher,
    "publish_state",
    mock.MagicMock(side_effect=mock_lv_ac_xport.MockLiveActionPublisher.publish_state),
)
@mock.patch.object(
    wf_ex_xport.WorkflowExecutionPublisher,
    "publish_create",
    mock.MagicMock(
        side_effect=mock_wf_ex_xport.MockWorkflowExecutionPublisher.publish_create
    ),
)
@mock.patch.object(
    wf_ex_xport.WorkflowExecutionPublisher,
    "publish_state",
    mock.MagicMock(
        side_effect=mock_wf_ex_xport.MockWorkflowExecutionPublisher.publish_state
    ),
)
class OrquestaNotifyTest(st2tests.ExecutionDbTestCase):
    @classmethod
    def setUpClass(cls):
        super(OrquestaNotifyTest, cls).setUpClass()

        # Register runners.
        runnersregistrar.register_runners()

        # Register test pack(s).
        actions_registrar = actionsregistrar.ActionsRegistrar(
            use_pack_cache=False, fail_on_failure=True
        )

        for pack in PACKS:
            actions_registrar.register_from_pack(pack)

    def test_no_notify(self):
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, "sequential.yaml")
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db, ac_ex_db = action_service.request(lv_ac_db)

        # Assert action execution is running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_RUNNING)
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]
        self.assertEqual(wf_ex_db.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Check that notify is setup correctly in the db record.
        self.assertDictEqual(wf_ex_db.notify, {})

    def test_no_notify_task_list(self):
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, "sequential.yaml")
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db.notify = notify_api_models.NotificationsHelper.to_model(MOCK_NOTIFY)
        lv_ac_db, ac_ex_db = action_service.request(lv_ac_db)

        # Assert action execution is running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_RUNNING)
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]
        self.assertEqual(wf_ex_db.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Check that notify is setup correctly in the db record.
        expected_notify = {"config": MOCK_NOTIFY, "tasks": []}

        self.assertDictEqual(wf_ex_db.notify, expected_notify)

    def test_custom_notify_task_list(self):
        wf_input = {"notify": ["task1"]}
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, "sequential.yaml")
        lv_ac_db = lv_db_models.LiveActionDB(
            action=wf_meta["name"], parameters=wf_input
        )
        lv_ac_db.notify = notify_api_models.NotificationsHelper.to_model(MOCK_NOTIFY)
        lv_ac_db, ac_ex_db = action_service.request(lv_ac_db)

        # Assert action execution is running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_RUNNING)
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]
        self.assertEqual(wf_ex_db.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Check that notify is setup correctly in the db record.
        expected_notify = {"config": MOCK_NOTIFY, "tasks": wf_input["notify"]}

        self.assertDictEqual(wf_ex_db.notify, expected_notify)

    def test_default_notify_task_list(self):
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, "notify.yaml")
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db.notify = notify_api_models.NotificationsHelper.to_model(MOCK_NOTIFY)
        lv_ac_db, ac_ex_db = action_service.request(lv_ac_db)

        # Assert action execution is running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_RUNNING)
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]
        self.assertEqual(wf_ex_db.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Check that notify is setup correctly in the db record.
        expected_notify = {"config": MOCK_NOTIFY, "tasks": ["task1", "task2", "task3"]}

        self.assertDictEqual(wf_ex_db.notify, expected_notify)

    def test_notify_task_list_bad_item_value(self):
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, "sequential.yaml")
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db.notify = notify_api_models.NotificationsHelper.to_model(MOCK_NOTIFY)

        expected_schema_failure_test_cases = [
            "task1",  # Notify must be type of list.
            [123],  # Item has to be type of string.
            [""],  # String value cannot be empty.
            ["  "],  # String value cannot be just spaces.
            ["      "],  # String value cannot be just tabs.
            ["init task"],  # String value cannot have space.
            ["init-task"],  # String value cannot have dash.
            ["task1", "task1"],  # String values have to be unique.
        ]

        for notify_tasks in expected_schema_failure_test_cases:
            lv_ac_db.parameters = {"notify": notify_tasks}

            try:
                self.assertRaises(
                    jsonschema.ValidationError, action_service.request, lv_ac_db
                )
            except Exception as e:
                raise AssertionError("%s: %s" % (six.text_type(e), notify_tasks))

    def test_notify_task_list_nonexistent_task(self):
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, "sequential.yaml")
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db.notify = notify_api_models.NotificationsHelper.to_model(MOCK_NOTIFY)

        lv_ac_db.parameters = {"notify": ["init_task"]}
        lv_ac_db, ac_ex_db = action_service.request(lv_ac_db)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))

        expected_result = {
            "output": None,
            "errors": [
                {
                    "message": (
                        "The following tasks in the notify parameter do not "
                        "exist in the workflow definition: init_task."
                    )
                }
            ],
        }

        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(lv_ac_db.result, expected_result)

    def test_notify_task_list_item_value(self):
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, "sequential.yaml")
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db.notify = notify_api_models.NotificationsHelper.to_model(MOCK_NOTIFY)

        expected_schema_success_test_cases = [[], ["task1"], ["task1", "task2"]]

        for notify_tasks in expected_schema_success_test_cases:
            lv_ac_db.parameters = {"notify": notify_tasks}
            lv_ac_db, ac_ex_db = action_service.request(lv_ac_db)
            lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
            self.assertEqual(
                lv_ac_db.status, action_constants.LIVEACTION_STATUS_RUNNING
            )

    def test_cascade_notify_to_tasks(self):
        wf_input = {"notify": ["task2"]}
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, "sequential.yaml")
        lv_ac_db = lv_db_models.LiveActionDB(
            action=wf_meta["name"], parameters=wf_input
        )
        lv_ac_db.notify = notify_api_models.NotificationsHelper.to_model(MOCK_NOTIFY)
        lv_ac_db, ac_ex_db = action_service.request(lv_ac_db)

        # Assert action execution is running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_RUNNING)
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]
        self.assertEqual(wf_ex_db.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Assert task1 notify is not set.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task1"}
        tk1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk1_ex_db.id)
        )[0]
        tk1_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk1_ac_ex_db.liveaction["id"])
        self.assertIsNone(tk1_lv_ac_db.notify)
        self.assertEqual(
            tk1_ac_ex_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        self.assertFalse(notifier.Notifier._post_notify_triggers.called)
        notifier.Notifier._post_notify_triggers.reset_mock()

        # Handle task1 completion.
        workflow_service.handle_action_execution_completion(tk1_ac_ex_db)
        tk1_ex_db = wf_db_access.TaskExecution.get_by_id(tk1_ex_db.id)
        self.assertEqual(tk1_ex_db.status, wf_statuses.SUCCEEDED)
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.RUNNING)

        # Assert task2 notify is set.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task2"}
        tk2_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk2_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk2_ex_db.id)
        )[0]
        tk2_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk2_ac_ex_db.liveaction["id"])
        notify = notify_api_models.NotificationsHelper.from_model(
            notify_model=tk2_lv_ac_db.notify
        )
        self.assertEqual(notify, MOCK_NOTIFY)
        self.assertEqual(
            tk2_ac_ex_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        self.assertTrue(notifier.Notifier._post_notify_triggers.called)
        notifier.Notifier._post_notify_triggers.reset_mock()

        # Handle task2 completion.
        workflow_service.handle_action_execution_completion(tk2_ac_ex_db)
        tk2_ex_db = wf_db_access.TaskExecution.get_by_id(tk2_ex_db.id)
        self.assertEqual(tk2_ex_db.status, wf_statuses.SUCCEEDED)
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.RUNNING)

        # Assert task3 notify is not set.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task3"}
        tk3_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk3_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk3_ex_db.id)
        )[0]
        tk3_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk3_ac_ex_db.liveaction["id"])
        self.assertIsNone(tk3_lv_ac_db.notify)
        self.assertEqual(
            tk3_ac_ex_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        self.assertFalse(notifier.Notifier._post_notify_triggers.called)
        notifier.Notifier._post_notify_triggers.reset_mock()

        # Handle task3 completion.
        workflow_service.handle_action_execution_completion(tk3_ac_ex_db)
        tk3_ex_db = wf_db_access.TaskExecution.get_by_id(tk3_ex_db.id)
        self.assertEqual(tk3_ex_db.status, wf_statuses.SUCCEEDED)

        # Assert workflow is completed.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.SUCCEEDED)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db.id))
        self.assertEqual(ac_ex_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertTrue(notifier.Notifier._post_notify_triggers.called)
        notifier.Notifier._post_notify_triggers.reset_mock()

    def test_notify_task_list_for_task_with_notify(self):
        wf_meta = base.get_wf_fixture_meta_data(
            TEST_PACK_PATH, "subworkflow-with-notify-task.yaml"
        )
        lv_ac_db = lv_db_models.LiveActionDB(
            action=wf_meta["name"], parameters={"notify": ["task2"]}
        )
        lv_ac_db.notify = notify_api_models.NotificationsHelper.to_model(MOCK_NOTIFY)
        lv_ac_db, ac_ex_db = action_service.request(lv_ac_db)

        # Assert action execution is running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_RUNNING)
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]
        self.assertEqual(wf_ex_db.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Assert task1 notify is not set.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task1"}
        tk1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk1_ex_db.id)
        )[0]
        tk1_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk1_ac_ex_db.liveaction["id"])
        self.assertIsNone(tk1_lv_ac_db.notify)
        # Assert task2 notify is set.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task2"}
        tk2_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk2_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk2_ex_db.id)
        )[0]
        tk2_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk2_ac_ex_db.liveaction["id"])
        notify = notify_api_models.NotificationsHelper.from_model(
            notify_model=tk2_lv_ac_db.notify
        )
        self.assertEqual(notify, MOCK_NOTIFY)

    def test_no_notify_for_task_with_notify(self):
        wf_meta = base.get_wf_fixture_meta_data(
            TEST_PACK_PATH, "subworkflow-with-notify-task.yaml"
        )
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db, ac_ex_db = action_service.request(lv_ac_db)

        # Assert action execution is running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_RUNNING)
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]
        self.assertEqual(wf_ex_db.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Assert task1 notify is not set.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task1"}
        tk1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk1_ex_db.id)
        )[0]
        tk1_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk1_ac_ex_db.liveaction["id"])
        self.assertIsNone(tk1_lv_ac_db.notify)

        # Assert task2 notify is not set.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task2"}
        tk2_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk2_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk2_ex_db.id)
        )[0]
        tk2_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk2_ac_ex_db.liveaction["id"])
        self.assertIsNone(tk2_lv_ac_db.notify)
