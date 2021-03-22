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

from st2api.controllers.resource import ResourceController
from st2common.models.api.trace import TraceAPI
from st2common.persistence.trace import Trace
from st2common.rbac.types import PermissionType

__all__ = ["TracesController"]


class TracesController(ResourceController):
    model = TraceAPI
    access = Trace
    supported_filters = {
        "trace_tag": "trace_tag",
        "execution": "action_executions.object_id",
        "rule": "rules.object_id",
        "trigger_instance": "trigger_instances.object_id",
    }

    query_options = {"sort": ["-start_timestamp", "trace_tag"]}

    def get_all(
        self,
        exclude_attributes=None,
        include_attributes=None,
        sort=None,
        offset=0,
        limit=None,
        requester_user=None,
        **raw_filters,
    ):
        # Use a custom sort order when filtering on a timestamp so we return a correct result as
        # expected by the user
        query_options = None
        if "sort_desc" in raw_filters and raw_filters["sort_desc"] == "True":
            query_options = {"sort": ["-start_timestamp", "trace_tag"]}
        elif "sort_asc" in raw_filters and raw_filters["sort_asc"] == "True":
            query_options = {"sort": ["+start_timestamp", "trace_tag"]}
        return self._get_all(
            exclude_fields=exclude_attributes,
            include_fields=include_attributes,
            sort=sort,
            offset=offset,
            limit=limit,
            query_options=query_options,
            raw_filters=raw_filters,
            requester_user=requester_user,
        )

    def get_one(self, id, requester_user):
        return self._get_one_by_id(
            id, requester_user=requester_user, permission_type=PermissionType.TRACE_VIEW
        )


traces_controller = TracesController()
