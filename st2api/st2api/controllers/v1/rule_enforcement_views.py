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

from st2common.models.api.rule_enforcement import RuleEnforcementViewAPI
from st2common.persistence.rule_enforcement import RuleEnforcement
from st2common.persistence.execution import ActionExecution
from st2api.controllers.v1.rule_enforcements import SUPPORTED_FILTERS
from st2api.controllers.v1.rule_enforcements import QUERY_OPTIONS
from st2api.controllers.v1.rule_enforcements import FILTER_TRANSFORM_FUNCTIONS
from st2common.rbac.types import PermissionType

from st2api.controllers.resource import ResourceController

__all__ = [
    'RuleEnforcementViewController'
]


class RuleEnforcementViewController(ResourceController):
    """
    API controller which adds some extra information to the rule enforcement object so it makes
    more efficient for UI and clients to render rule enforcement object.

    Right now in case a trigger instance matched an execution and execution was triggered, it also
    includes action input parameters for the trigger action.
    """

    model = RuleEnforcementViewAPI
    access = RuleEnforcement

    query_options = QUERY_OPTIONS

    supported_filters = SUPPORTED_FILTERS
    filter_transform_functions = FILTER_TRANSFORM_FUNCTIONS

    def get_all(self, sort=None, offset=0, limit=None, requester_user=None, **raw_filters):
        rule_enforcement_apis = super(RuleEnforcementViewController, self)._get_all(sort=sort,
                                                               offset=offset,
                                                               limit=limit,
                                                               raw_filters=raw_filters,
                                                               requester_user=requester_user)

        rule_enforcement_apis.json = self._append_view_properties(rule_enforcement_apis.json)
        return rule_enforcement_apis

    def get_one(self, id, requester_user):
        rule_enforcement_api = super(RuleEnforcementViewController,
                     self)._get_one_by_id(id, requester_user=requester_user,
                                          permission_type=PermissionType.RULE_ENFORCEMENT_VIEW)
        rule_enforcement_api = self._append_view_properties([rule_enforcement_api.__json__()])[0]
        return rule_enforcement_api

    def _append_view_properties(self, rule_enforcement_apis):
        execution_ids = []

        for rule_enforcement_api in rule_enforcement_apis:
            if rule_enforcement_api.get('execution_id', None):
                execution_ids.append(rule_enforcement_api['execution_id'])

        # NOTE: Executions contain a lot of field and could contain a lot of data so we only
        # retrieve fields we need
        execution_dbs = ActionExecution.query(id__in=execution_ids,
                                              only_fields=['id', 'action.ref', 'parameters'])
        execution_dbs_by_id = {}

        for execution_db in execution_dbs:
            execution_dbs_by_id[str(execution_db.id)] = execution_db

        # Ammend rule enforcement objects with additional data
        for rule_enforcement_api in rule_enforcement_apis:
            rule_enforcement_api['execution'] = {}
            execution_id = rule_enforcement_api.get('execution_id', None)

            if not execution_id:
                continue

            execution_db = execution_dbs_by_id.get(execution_id, None)

            if not execution_db:
                continue

            rule_enforcement_api['execution'] = {
                'action': {
                    'ref': execution_db['action']['ref']
                },
                'parameters': execution_db['parameters']
            }

        return rule_enforcement_apis


rule_enforcement_view_controller = RuleEnforcementViewController()
