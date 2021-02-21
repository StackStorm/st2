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

import mongoengine as me

from st2common.constants import types
from st2common import fields as db_field_types
from st2common import log as logging
from st2common.models.db import stormbase
from st2common.fields import JSONDictEscapedFieldCompatibilityField
from st2common.util import date as date_utils


__all__ = [
    'WorkflowExecutionDB',
    'TaskExecutionDB'
]


LOG = logging.getLogger(__name__)


class WorkflowExecutionDB(stormbase.StormFoundationDB, stormbase.ChangeRevisionFieldMixin):
    RESOURCE_TYPE = types.ResourceType.EXECUTION

    # TODO: Explore for which fields we could use new JSONDictField which is up to 10 or more times
    # more efficient when storing and reading data, especially for fields with large dicts. Those
    # fields need to be treated as opaque binary blob to database and we shouldn't directly perform
    # queries on those field values.

    action_execution = me.StringField(required=True)
    spec = JSONDictEscapedFieldCompatibilityField()
    graph = JSONDictEscapedFieldCompatibilityField()
    input = JSONDictEscapedFieldCompatibilityField()
    notify = me.DictField()
    context = JSONDictEscapedFieldCompatibilityField()
    state = JSONDictEscapedFieldCompatibilityField()
    status = me.StringField(required=True)
    output = JSONDictEscapedFieldCompatibilityField()
    errors = stormbase.EscapedDynamicField()
    start_timestamp = db_field_types.ComplexDateTimeField(default=date_utils.get_datetime_utc_now)
    end_timestamp = db_field_types.ComplexDateTimeField()

    meta = {
        'indexes': [
            {'fields': ['action_execution']}
        ]
    }


class TaskExecutionDB(stormbase.StormFoundationDB, stormbase.ChangeRevisionFieldMixin):
    RESOURCE_TYPE = types.ResourceType.EXECUTION

    # TODO: Explore for which fields we could use new JSONDictField which is up to 10 or more times
    # more efficient when storing and reading data, especially for fields with large dicts. Those
    # fields need to be treated as opaque binary blob to database and we shouldn't directly perform
    # queries on those field values.

    workflow_execution = me.StringField(required=True)
    task_name = me.StringField(required=True)
    task_id = me.StringField(required=True)
    task_route = me.IntField(required=True, min_value=0)
    task_spec = JSONDictEscapedFieldCompatibilityField()
    delay = me.IntField(min_value=0)
    itemized = me.BooleanField(default=False)
    items_count = me.IntField(min_value=0)
    items_concurrency = me.IntField(min_value=1)
    context = JSONDictEscapedFieldCompatibilityField()
    status = me.StringField(required=True)
    result = JSONDictEscapedFieldCompatibilityField()
    start_timestamp = db_field_types.ComplexDateTimeField(default=date_utils.get_datetime_utc_now)
    end_timestamp = db_field_types.ComplexDateTimeField()

    meta = {
        'indexes': [
            {'fields': ['workflow_execution']},
            {'fields': ['task_id']},
            {'fields': ['task_id', 'task_route']},
            {'fields': ['workflow_execution', 'task_id']},
            {'fields': ['workflow_execution', 'task_id', 'task_route']}
        ]
    }


MODELS = [
    WorkflowExecutionDB,
    TaskExecutionDB
]
