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

from st2common import log as logging
from st2common.models.db import stormbase
from st2common.models.db import ChangeRevisionMongoDBAccess
from st2common.fields import ComplexDateTimeField
from st2common.util import date as date_utils
from st2common.constants.types import ResourceType

__all__ = [
    "ActionExecutionSchedulingQueueItemDB",
]


LOG = logging.getLogger(__name__)


class ActionExecutionSchedulingQueueItemDB(
    stormbase.StormFoundationDB, stormbase.ChangeRevisionFieldMixin
):
    """
    A model which represents a request for execution to be scheduled.

    Those models are picked up by the scheduler and scheduled to be ran by an action
    runner.
    """

    RESOURCE_TYPE = ResourceType.EXECUTION_REQUEST
    UID_FIELDS = ["id"]

    liveaction_id = me.StringField(
        required=True,
        help_text="Foreign key to the LiveActionDB which is to be scheduled",
    )
    action_execution_id = me.StringField(
        help_text="Foreign key to the ActionExecutionDB which is to be scheduled"
    )
    original_start_timestamp = ComplexDateTimeField(
        default=date_utils.get_datetime_utc_now,
        help_text="The timestamp when the liveaction was created and originally be scheduled to "
        "run.",
    )
    scheduled_start_timestamp = ComplexDateTimeField(
        default=date_utils.get_datetime_utc_now,
        help_text="The timestamp when liveaction is scheduled to run.",
    )
    delay = me.IntField()
    handling = me.BooleanField(
        default=False,
        help_text="Flag indicating if this item is currently being handled / "
        "processed by a scheduler service",
    )

    meta = {
        "indexes": [
            # NOTE: We limit index names to 65 characters total for compatibility with AWS
            # DocumentDB.
            # See https://github.com/StackStorm/st2/pull/4690 for details.
            {"fields": ["action_execution_id"], "name": "ac_exc_id"},
            {"fields": ["liveaction_id"], "name": "lv_ac_id"},
            {"fields": ["original_start_timestamp"], "name": "orig_s_ts"},
            {"fields": ["scheduled_start_timestamp"], "name": "schd_s_ts"},
            # Adding a union index speeds up the query action_execution_scheduling_queue_item_d_b
            {
                "fields": ["scheduled_start_timestamp", "original_start_timestamp"],
                "name": "schd_orig_s_ts",
            },
        ]
    }


MODELS = [ActionExecutionSchedulingQueueItemDB]
EXECUTION_QUEUE_ACCESS = ChangeRevisionMongoDBAccess(
    ActionExecutionSchedulingQueueItemDB
)
