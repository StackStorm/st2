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

from st2common.models.api.rule_enforcement import RuleEnforcementViewAPI
from st2common.models.api.trigger import TriggerInstanceAPI
from st2common.models.api.execution import ActionExecutionAPI
from st2common.persistence.rule_enforcement import RuleEnforcement
from st2common.persistence.execution import ActionExecution
from st2common.persistence.trigger import TriggerInstance
from st2api.controllers.v1.rule_enforcements import SUPPORTED_FILTERS
from st2api.controllers.v1.rule_enforcements import QUERY_OPTIONS
from st2api.controllers.v1.rule_enforcements import FILTER_TRANSFORM_FUNCTIONS
from st2common.rbac.types import PermissionType

from st2api.controllers.resource import ResourceController

__all__ = ["RuleEnforcementViewController"]


class RuleEnforcementViewController(ResourceController):
    """
    API controller which adds some extra information to the rule enforcement object so it makes
    more efficient for UI and clients to render rule enforcement object.

    Right now we include those fields:

    * trigger_instance object for each rule enforcement object
    * subset of an execution object in case execution was triggered
    """

    model = RuleEnforcementViewAPI
    access = RuleEnforcement

    query_options = QUERY_OPTIONS

    supported_filters = SUPPORTED_FILTERS
    filter_transform_functions = FILTER_TRANSFORM_FUNCTIONS

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
        rule_enforcement_apis = super(RuleEnforcementViewController, self)._get_all(
            exclude_fields=exclude_attributes,
            include_fields=include_attributes,
            sort=sort,
            offset=offset,
            limit=limit,
            raw_filters=raw_filters,
            requester_user=requester_user,
        )

        rule_enforcement_apis.json = self._append_view_properties(
            rule_enforcement_apis.json
        )
        return rule_enforcement_apis

    def get_one(self, id, requester_user):
        rule_enforcement_api = super(
            RuleEnforcementViewController, self
        )._get_one_by_id(
            id,
            requester_user=requester_user,
            permission_type=PermissionType.RULE_ENFORCEMENT_VIEW,
        )
        rule_enforcement_api = self._append_view_properties(
            [rule_enforcement_api.__json__()]
        )[0]
        return rule_enforcement_api

    def _append_view_properties(self, rule_enforcement_apis):
        """
        Method which appends corresponding execution (if available) and trigger instance object
        properties.
        """
        trigger_instance_ids = set([])
        execution_ids = []

        for rule_enforcement_api in rule_enforcement_apis:
            if rule_enforcement_api.get("trigger_instance_id", None):
                trigger_instance_ids.add(
                    str(rule_enforcement_api["trigger_instance_id"])
                )

            if rule_enforcement_api.get("execution_id", None):
                execution_ids.append(rule_enforcement_api["execution_id"])

        # 1. Retrieve corresponding execution objects
        # NOTE: Executions contain a lot of field and could contain a lot of data so we only
        # retrieve fields we need
        only_fields = [
            "id",
            "action.ref",
            "action.parameters",
            "runner.name",
            "runner.runner_parameters",
            "parameters",
            "status",
        ]
        execution_dbs = ActionExecution.query(
            id__in=execution_ids, only_fields=only_fields
        )

        execution_dbs_by_id = {}
        for execution_db in execution_dbs:
            execution_dbs_by_id[str(execution_db.id)] = execution_db

        # 2. Retrieve corresponding trigger instance objects
        trigger_instance_dbs = TriggerInstance.query(id__in=list(trigger_instance_ids))

        trigger_instance_dbs_by_id = {}

        for trigger_instance_db in trigger_instance_dbs:
            trigger_instance_dbs_by_id[
                str(trigger_instance_db.id)
            ] = trigger_instance_db

        # Ammend rule enforcement objects with additional data
        for rule_enforcement_api in rule_enforcement_apis:
            rule_enforcement_api["trigger_instance"] = {}
            rule_enforcement_api["execution"] = {}

            trigger_instance_id = rule_enforcement_api.get("trigger_instance_id", None)
            execution_id = rule_enforcement_api.get("execution_id", None)

            trigger_instance_db = trigger_instance_dbs_by_id.get(
                trigger_instance_id, None
            )
            execution_db = execution_dbs_by_id.get(execution_id, None)

            if trigger_instance_db:
                trigger_instance_api = TriggerInstanceAPI.from_model(
                    trigger_instance_db
                )
                rule_enforcement_api["trigger_instance"] = trigger_instance_api

            if execution_db:
                execution_api = ActionExecutionAPI.from_model(execution_db)
                rule_enforcement_api["execution"] = execution_api

        return rule_enforcement_apis


rule_enforcement_view_controller = RuleEnforcementViewController()
