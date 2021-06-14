# Copyright 2021 The StackStorm Authors.
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

import os
import sys

import datetime

from st2common.constants import action as action_constants
from st2common.models.db import stormbase
from st2common.models.db.execution import ActionExecutionDB
from st2common.models.db.liveaction import LiveActionDB
from st2common.models.db.workflow import WorkflowExecutionDB
from st2common.models.db.workflow import TaskExecutionDB
from st2common.models.db.trigger import TriggerInstanceDB
from st2common.persistence.execution import ActionExecution
from st2common.persistence.liveaction import LiveAction
from st2common.persistence.workflow import WorkflowExecution
from st2common.persistence.workflow import TaskExecution
from st2common.persistence.trigger import TriggerInstance
from st2common.constants.triggers import TRIGGER_INSTANCE_PROCESSED
from st2common.constants.triggers import TRIGGER_INSTANCE_PENDING

from st2tests import DbTestCase

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(
    os.path.abspath(os.path.join(BASE_DIR, "../../../bin/migrations/v3.5/"))
)

import st2_migrate_db_dict_field_values as migration_module


MOCK_RESULT_1 = {
    "foo": "bar1",
    "bar": 1,
    "baz": None,
}

MOCK_RESULT_2 = {
    "foo": "bar2",
    "bar": 2,
    "baz": False,
}

MOCK_PAYLOAD_1 = {"yaaaas": "le payload!"}

MOCK_PAYLOAD_2 = {"yaaaas": "le payload! 2"}

# NOTE: We define those classes and set allow_inheritance inside the methods so importing this
# module doesn't have side affect and break / affect other tests


class DBFieldsMigrationScriptTestCase(DbTestCase):
    @classmethod
    def tearDownClass(cls):
        ActionExecutionDB._meta["allow_inheritance"] = False
        LiveActionDB._meta["allow_inheritance"] = False
        WorkflowExecutionDB._meta["allow_inheritance"] = False
        TaskExecutionDB._meta["allow_inheritance"] = False
        TriggerInstanceDB._meta["allow_inheritance"] = False

    def test_migrate_executions_related_liveaction_doesnt_exist(self):
        pass

    def test_migrate_executions(self):
        ActionExecutionDB._meta["allow_inheritance"] = True
        LiveActionDB._meta["allow_inheritance"] = True

        class ActionExecutionDB_OldFieldType(ActionExecutionDB):
            result = stormbase.EscapedDynamicField(default={})

        class LiveActionDB_OldFieldType(LiveActionDB):
            result = stormbase.EscapedDynamicField(default={})

        execution_dbs = ActionExecution.query(
            __raw__={
                "result": {
                    "$not": {
                        "$type": "binData",
                    },
                }
            }
        )
        self.assertEqual(len(execution_dbs), 0)
        execution_dbs = ActionExecution.query(
            __raw__={
                "result": {
                    "$type": "object",
                },
            }
        )
        self.assertEqual(len(execution_dbs), 0)

        # 1. Insert data in old format
        liveaction_1_db = LiveActionDB_OldFieldType()
        liveaction_1_db.action = "foo.bar"
        liveaction_1_db.status = action_constants.LIVEACTION_STATUS_FAILED
        liveaction_1_db.result = MOCK_RESULT_1
        liveaction_1_db.start_timestamp = datetime.datetime.utcnow().replace(
            tzinfo=datetime.timezone.utc
        )
        liveaction_1_db = LiveAction.add_or_update(liveaction_1_db, publish=False)

        execution_1_db = ActionExecutionDB_OldFieldType()
        execution_1_db.action = {"a": 1}
        execution_1_db.runner = {"a": 1}
        execution_1_db.liveaction = {"id": liveaction_1_db.id}
        execution_1_db.status = action_constants.LIVEACTION_STATUS_FAILED
        execution_1_db.result = MOCK_RESULT_1
        execution_1_db.start_timestamp = datetime.datetime.utcnow().replace(
            tzinfo=datetime.timezone.utc
        )

        execution_1_db = ActionExecution.add_or_update(execution_1_db, publish=False)

        # This execution is not in a final state yet so it should not be migrated
        liveaction_2_db = LiveActionDB_OldFieldType()
        liveaction_2_db.action = "foo.bar2"
        liveaction_2_db.status = action_constants.LIVEACTION_STATUS_RUNNING
        liveaction_2_db.result = MOCK_RESULT_2
        liveaction_2_db.start_timestamp = datetime.datetime.utcnow().replace(
            tzinfo=datetime.timezone.utc
        )

        liveaction_2_db = LiveAction.add_or_update(liveaction_2_db, publish=False)

        execution_2_db = ActionExecutionDB_OldFieldType()
        execution_2_db.action = {"a": 2}
        execution_2_db.runner = {"a": 2}
        execution_2_db.liveaction = {"id": liveaction_2_db.id}
        execution_2_db.status = action_constants.LIVEACTION_STATUS_RUNNING
        execution_2_db.result = MOCK_RESULT_2
        execution_2_db.start_timestamp = datetime.datetime.utcnow().replace(
            tzinfo=datetime.timezone.utc
        )

        execution_2_db = ActionExecution.add_or_update(execution_2_db, publish=False)

        # This object is older than the default threshold so it should not be migrated
        execution_3_db = ActionExecutionDB_OldFieldType()
        execution_3_db.action = {"a": 2}
        execution_3_db.runner = {"a": 2}
        execution_3_db.liveaction = {"id": liveaction_2_db.id}
        execution_3_db.status = action_constants.LIVEACTION_STATUS_SUCCEEDED
        execution_3_db.result = MOCK_RESULT_1
        execution_3_db.start_timestamp = datetime.datetime.utcfromtimestamp(0).replace(
            tzinfo=datetime.timezone.utc
        )

        execution_3_db = ActionExecution.add_or_update(execution_3_db, publish=False)

        # Verify data has been inserted in old format
        execution_dbs = ActionExecution.query(
            __raw__={
                "result": {
                    "$type": "object",
                },
            }
        )
        self.assertEqual(len(execution_dbs), 3)
        execution_dbs = ActionExecution.query(
            __raw__={
                "result": {
                    "$not": {
                        "$type": "binData",
                    },
                }
            }
        )
        self.assertEqual(len(execution_dbs), 3)
        execution_dbs = ActionExecution.query(
            __raw__={
                "result": {
                    "$type": "binData",
                },
            }
        )
        self.assertEqual(len(execution_dbs), 0)

        liveaction_dbs = LiveAction.query(
            __raw__={
                "result": {
                    "$type": "object",
                },
            }
        )
        self.assertEqual(len(liveaction_dbs), 2)
        liveaction_dbs = LiveAction.query(
            __raw__={
                "result": {
                    "$not": {
                        "$type": "binData",
                    },
                }
            }
        )
        self.assertEqual(len(liveaction_dbs), 2)
        liveaction_dbs = LiveAction.query(
            __raw__={
                "result": {
                    "$type": "binData",
                },
            }
        )
        self.assertEqual(len(liveaction_dbs), 0)

        # Update inserted documents and remove special _cls field added by mongoengine. We need to
        # do that here due to how mongoengine works with subclasses.
        ActionExecution.query(
            __raw__={
                "result": {
                    "$type": "object",
                },
            }
        ).update(set___cls="ActionExecutionDB")

        LiveAction.query(
            __raw__={
                "result": {
                    "$type": "object",
                },
            }
        ).update(set___cls="LiveActionDB")

        # 2. Run migration
        start_dt = datetime.datetime.utcnow().replace(
            tzinfo=datetime.timezone.utc
        ) - datetime.timedelta(hours=2)
        end_dt = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
        migration_module.migrate_executions(start_dt=start_dt, end_dt=end_dt)

        # 3. Verify data has been migrated - only 1 item should have been migrated since it's in a
        # completed state
        execution_dbs = ActionExecution.query(
            __raw__={
                "result": {
                    "$type": "object",
                },
            }
        )
        self.assertEqual(len(execution_dbs), 2)
        execution_dbs = ActionExecution.query(
            __raw__={
                "result": {
                    "$type": "binData",
                },
            }
        )
        self.assertEqual(len(execution_dbs), 1)

        execution_db_1_retrieved = ActionExecution.get_by_id(execution_1_db.id)
        self.assertEqual(execution_db_1_retrieved.result, MOCK_RESULT_1)

        execution_db_2_retrieved = ActionExecution.get_by_id(execution_2_db.id)
        self.assertEqual(execution_db_2_retrieved.result, MOCK_RESULT_2)

        liveaction_db_1_retrieved = LiveAction.get_by_id(liveaction_1_db.id)
        self.assertEqual(liveaction_db_1_retrieved.result, MOCK_RESULT_1)

        liveaction_db_2_retrieved = LiveAction.get_by_id(liveaction_2_db.id)
        self.assertEqual(liveaction_db_2_retrieved.result, MOCK_RESULT_2)

    def test_migrate_workflows(self):
        WorkflowExecutionDB._meta["allow_inheritance"] = True
        TaskExecutionDB._meta["allow_inheritance"] = True

        class WorkflowExecutionDB_OldFieldType(WorkflowExecutionDB):
            input = stormbase.EscapedDictField()
            context = stormbase.EscapedDictField()
            state = stormbase.EscapedDictField()
            output = stormbase.EscapedDictField()

        class TaskExecutionDB_OldFieldType(TaskExecutionDB):
            task_spec = stormbase.EscapedDictField()
            context = stormbase.EscapedDictField()
            result = stormbase.EscapedDictField()

        workflow_execution_dbs = WorkflowExecution.query(
            __raw__={
                "output": {
                    "$not": {
                        "$type": "binData",
                    },
                }
            }
        )
        self.assertEqual(len(workflow_execution_dbs), 0)
        workflow_execution_dbs = WorkflowExecution.query(
            __raw__={
                "output": {
                    "$type": "object",
                },
            }
        )
        self.assertEqual(len(workflow_execution_dbs), 0)

        task_execution_dbs = TaskExecution.query(
            __raw__={
                "result": {
                    "$not": {
                        "$type": "binData",
                    },
                }
            }
        )
        self.assertEqual(len(task_execution_dbs), 0)
        task_execution_dbs = TaskExecution.query(
            __raw__={
                "result": {
                    "$type": "object",
                },
            }
        )
        self.assertEqual(len(task_execution_dbs), 0)

        # 1. Insert data in old format
        workflow_execution_1_db = WorkflowExecutionDB_OldFieldType()
        workflow_execution_1_db.input = MOCK_RESULT_1
        workflow_execution_1_db.context = MOCK_RESULT_1
        workflow_execution_1_db.state = MOCK_RESULT_1
        workflow_execution_1_db.output = MOCK_RESULT_1
        workflow_execution_1_db.status = action_constants.LIVEACTION_STATUS_SUCCEEDED
        workflow_execution_1_db.action_execution = "a"
        workflow_execution_1_db = WorkflowExecution.add_or_update(
            workflow_execution_1_db, publish=False
        )

        task_execution_1_db = TaskExecutionDB_OldFieldType()
        task_execution_1_db.task_spec = MOCK_RESULT_1
        task_execution_1_db.context = MOCK_RESULT_1
        task_execution_1_db.result = MOCK_RESULT_1
        task_execution_1_db.status = action_constants.LIVEACTION_STATUS_SUCCEEDED
        task_execution_1_db.workflow_execution = "a"
        task_execution_1_db.task_name = "a"
        task_execution_1_db.task_id = "a"
        task_execution_1_db.task_route = 1
        task_execution_1_db = TaskExecution.add_or_update(
            task_execution_1_db, publish=False
        )

        workflow_execution_2_db = WorkflowExecutionDB_OldFieldType()
        workflow_execution_2_db.input = MOCK_RESULT_2
        workflow_execution_2_db.context = MOCK_RESULT_2
        workflow_execution_2_db.state = MOCK_RESULT_2
        workflow_execution_2_db.output = MOCK_RESULT_2
        workflow_execution_2_db.status = action_constants.LIVEACTION_STATUS_RUNNING
        workflow_execution_2_db.action_execution = "b"
        workflow_execution_2_db = WorkflowExecution.add_or_update(
            workflow_execution_2_db, publish=False
        )

        task_execution_2_db = TaskExecutionDB_OldFieldType()
        task_execution_2_db.task_spec = MOCK_RESULT_2
        task_execution_2_db.context = MOCK_RESULT_2
        task_execution_2_db.result = MOCK_RESULT_2
        task_execution_2_db.status = action_constants.LIVEACTION_STATUS_RUNNING
        task_execution_2_db.workflow_execution = "b"
        task_execution_2_db.task_name = "b"
        task_execution_2_db.task_id = "b"
        task_execution_2_db.task_route = 2
        task_execution_2_db = TaskExecution.add_or_update(
            task_execution_2_db, publish=False
        )

        # This object is older than the default threshold so it should not be migrated
        workflow_execution_3_db = WorkflowExecutionDB_OldFieldType()
        workflow_execution_3_db.input = MOCK_RESULT_2
        workflow_execution_3_db.context = MOCK_RESULT_2
        workflow_execution_3_db.state = MOCK_RESULT_2
        workflow_execution_3_db.output = MOCK_RESULT_2
        workflow_execution_3_db.status = action_constants.LIVEACTION_STATUS_SUCCEEDED
        workflow_execution_3_db.action_execution = "b"
        workflow_execution_3_db.start_timestamp = datetime.datetime.utcfromtimestamp(
            0
        ).replace(tzinfo=datetime.timezone.utc)
        workflow_execution_3_db = WorkflowExecution.add_or_update(
            workflow_execution_3_db, publish=False
        )

        task_execution_3_db = TaskExecutionDB_OldFieldType()
        task_execution_3_db.task_spec = MOCK_RESULT_2
        task_execution_3_db.context = MOCK_RESULT_2
        task_execution_3_db.result = MOCK_RESULT_2
        task_execution_3_db.status = action_constants.LIVEACTION_STATUS_SUCCEEDED
        task_execution_3_db.workflow_execution = "b"
        task_execution_3_db.task_name = "b"
        task_execution_3_db.task_id = "b"
        task_execution_3_db.task_route = 2
        task_execution_3_db.start_timestamp = datetime.datetime.utcfromtimestamp(
            0
        ).replace(tzinfo=datetime.timezone.utc)
        task_execution_3_db = TaskExecution.add_or_update(
            task_execution_3_db, publish=False
        )

        # Update inserted documents and remove special _cls field added by mongoengine. We need to
        # do that here due to how mongoengine works with subclasses.
        WorkflowExecution.query(
            __raw__={
                "input": {
                    "$type": "object",
                },
            }
        ).update(set___cls="WorkflowExecutionDB")

        TaskExecution.query(
            __raw__={
                "result": {
                    "$type": "object",
                },
            }
        ).update(set___cls="TaskExecutionDB")

        # 2. Run migration
        start_dt = datetime.datetime.utcnow().replace(
            tzinfo=datetime.timezone.utc
        ) - datetime.timedelta(hours=2)
        end_dt = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
        migration_module.migrate_workflow_objects(start_dt=start_dt, end_dt=end_dt)

        # 3. Verify data has been migrated - only 1 item should have been migrated since it's in a
        # completed state
        workflow_execution_dbs = WorkflowExecution.query(
            __raw__={
                "output": {
                    "$type": "binData",
                },
            }
        )
        self.assertEqual(len(workflow_execution_dbs), 1)
        workflow_execution_dbs = WorkflowExecution.query(
            __raw__={
                "output": {
                    "$type": "object",
                },
            }
        )
        self.assertEqual(len(workflow_execution_dbs), 2)

        task_execution_dbs = TaskExecution.query(
            __raw__={
                "result": {
                    "$type": "binData",
                },
            }
        )
        self.assertEqual(len(task_execution_dbs), 1)
        task_execution_dbs = TaskExecution.query(
            __raw__={
                "result": {
                    "$type": "object",
                },
            }
        )
        self.assertEqual(len(task_execution_dbs), 2)

        workflow_execution_1_db_retrieved = WorkflowExecution.get_by_id(
            workflow_execution_1_db.id
        )
        self.assertEqual(workflow_execution_1_db_retrieved.input, MOCK_RESULT_1)
        self.assertEqual(workflow_execution_1_db_retrieved.context, MOCK_RESULT_1)
        self.assertEqual(workflow_execution_1_db_retrieved.state, MOCK_RESULT_1)
        self.assertEqual(workflow_execution_1_db_retrieved.output, MOCK_RESULT_1)

        workflow_execution_2_db_retrieved = WorkflowExecution.get_by_id(
            workflow_execution_2_db.id
        )
        self.assertEqual(workflow_execution_2_db_retrieved.input, MOCK_RESULT_2)
        self.assertEqual(workflow_execution_2_db_retrieved.context, MOCK_RESULT_2)
        self.assertEqual(workflow_execution_2_db_retrieved.state, MOCK_RESULT_2)
        self.assertEqual(workflow_execution_2_db_retrieved.output, MOCK_RESULT_2)

    def test_migrate_triggers(self):
        TriggerInstanceDB._meta["allow_inheritance"] = True

        class TriggerInstanceDB_OldFieldType(TriggerInstanceDB):
            payload = stormbase.EscapedDictField()

        trigger_instance_dbs = TriggerInstance.query(
            __raw__={
                "payload": {
                    "$not": {
                        "$type": "binData",
                    },
                }
            }
        )
        self.assertEqual(len(trigger_instance_dbs), 0)
        trigger_instance_dbs = TriggerInstance.query(
            __raw__={
                "payload": {
                    "$type": "object",
                },
            }
        )
        self.assertEqual(len(trigger_instance_dbs), 0)

        # 1. Insert data in old format
        trigger_instance_1_db = TriggerInstanceDB_OldFieldType()
        trigger_instance_1_db.payload = MOCK_PAYLOAD_1
        trigger_instance_1_db.status = TRIGGER_INSTANCE_PROCESSED
        trigger_instance_1_db.occurrence_time = datetime.datetime.utcnow()

        trigger_instance_1_db = TriggerInstance.add_or_update(
            trigger_instance_1_db, publish=False
        )

        trigger_instance_2_db = TriggerInstanceDB_OldFieldType()
        trigger_instance_2_db.payload = MOCK_PAYLOAD_2
        trigger_instance_2_db.status = TRIGGER_INSTANCE_PENDING
        trigger_instance_2_db.occurrence_time = datetime.datetime.utcnow()

        trigger_instance_2_db = TriggerInstance.add_or_update(
            trigger_instance_2_db, publish=False
        )

        # This object is older than the default threshold so it should not be migrated
        trigger_instance_3_db = TriggerInstanceDB_OldFieldType()
        trigger_instance_3_db.payload = MOCK_PAYLOAD_2
        trigger_instance_3_db.status = TRIGGER_INSTANCE_PROCESSED
        trigger_instance_3_db.occurrence_time = datetime.datetime.utcfromtimestamp(0)

        trigger_instance_3_db = TriggerInstance.add_or_update(
            trigger_instance_3_db, publish=False
        )

        # Verify data has been inserted in old format
        trigger_instance_dbs = TriggerInstance.query(
            __raw__={
                "payload": {
                    "$not": {
                        "$type": "binData",
                    },
                }
            }
        )
        self.assertEqual(len(trigger_instance_dbs), 3)
        trigger_instance_dbs = TriggerInstance.query(
            __raw__={
                "payload": {
                    "$type": "object",
                },
            }
        )
        self.assertEqual(len(trigger_instance_dbs), 3)

        # Update inserted documents and remove special _cls field added by mongoengine. We need to
        # do that here due to how mongoengine works with subclasses.
        TriggerInstance.query(
            __raw__={
                "payload": {
                    "$type": "object",
                },
            }
        ).update(set___cls="TriggerInstanceDB")

        # 2. Run migration
        start_dt = datetime.datetime.utcnow().replace(
            tzinfo=datetime.timezone.utc
        ) - datetime.timedelta(hours=2)
        end_dt = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
        migration_module.migrate_triggers(start_dt=start_dt, end_dt=end_dt)

        # 3. Verify data has been migrated - only 1 item should have been migrated since it's in a
        # completed state
        trigger_instance_dbs = TriggerInstance.query(
            __raw__={
                "payload": {
                    "$not": {
                        "$type": "binData",
                    },
                }
            }
        )

        # TODO: Also verify raw as_pymongo() bin field value
        self.assertEqual(len(trigger_instance_dbs), 2)
        trigger_instance_dbs = TriggerInstance.query(
            __raw__={
                "payload": {
                    "$type": "object",
                },
            }
        )
        self.assertEqual(len(trigger_instance_dbs), 2)

        trigger_instance_1_db_retrieved = TriggerInstance.get_by_id(
            trigger_instance_1_db.id
        )
        self.assertEqual(trigger_instance_1_db_retrieved.payload, MOCK_PAYLOAD_1)

        trigger_instance_2_db_retrieved = TriggerInstance.get_by_id(
            trigger_instance_2_db.id
        )
        self.assertEqual(trigger_instance_2_db_retrieved.payload, MOCK_PAYLOAD_2)
