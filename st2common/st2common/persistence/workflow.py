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

from st2common import transport
from st2common.models import db
from st2common.models.db import workflow as wf_db_models
from st2common.persistence import base as persistence


__all__ = ["WorkflowExecution", "TaskExecution", "TaskItemState"]


class WorkflowExecution(persistence.StatusBasedResource):
    impl = db.ChangeRevisionMongoDBAccess(wf_db_models.WorkflowExecutionDB)
    publisher = None

    @classmethod
    def _get_impl(cls):
        return cls.impl

    @classmethod
    def _get_publisher(cls):
        if not cls.publisher:
            cls.publisher = transport.workflow.WorkflowExecutionPublisher()

        return cls.publisher

    @classmethod
    def delete_by_query(cls, *args, **query):
        return cls._get_impl().delete_by_query(*args, **query)


class TaskExecution(persistence.StatusBasedResource):
    impl = db.ChangeRevisionMongoDBAccess(wf_db_models.TaskExecutionDB)
    publisher = None

    @classmethod
    def _get_impl(cls):
        return cls.impl

    @classmethod
    def delete_by_query(cls, *args, **query):
        return cls._get_impl().delete_by_query(*args, **query)


class TaskItemState(persistence.StatusBasedResource):
    impl = db.ChangeRevisionMongoDBAccess(wf_db_models.TaskItemStateDB)
    publisher = None

    @classmethod
    def _get_impl(cls):
        return cls.impl

    @classmethod
    def get_by_task_and_item(cls, task_execution_id, item_id):
        """
        Retrieve the state record for a specific item in a task execution.

        Args:
            task_execution_id: ID of the task execution
            item_id: ID of the specific item

        Returns:
            TaskItemStateDB: The state record for the specified item
        """
        return cls._get_impl().get(task_execution=task_execution_id, item_id=item_id)

    @classmethod
    def query_by_task_execution(cls, task_execution_id):
        """
        Retrieve all item state records for a task execution.

        Args:
            task_execution_id: ID of the task execution

        Returns:
            list: List of TaskItemStateDB objects for all items in the task
        """
        return cls.query(task_execution=task_execution_id)

    @classmethod
    def delete_by_query(cls, *args, **query):
        return cls._get_impl().delete_by_query(*args, **query)
