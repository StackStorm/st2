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

import six

from st2common import log as logging
from st2common.models.api.rule_enforcement import RuleEnforcementAPI
from st2common.persistence.rule_enforcement import RuleEnforcement
from st2common.util import isotime
from st2common.rbac.types import PermissionType

from st2api.controllers.resource import ResourceController

__all__ = [
    "RuleEnforcementController",
    "SUPPORTED_FILTERS",
    "QUERY_OPTIONS",
    "FILTER_TRANSFORM_FUNCTIONS",
]


http_client = six.moves.http_client

LOG = logging.getLogger(__name__)


SUPPORTED_FILTERS = {
    "rule_ref": "rule.ref",
    "rule_id": "rule.id",
    "execution": "execution_id",
    "trigger_instance": "trigger_instance_id",
    "enforced_at": "enforced_at",
    "enforced_at_gt": "enforced_at.gt",
    "enforced_at_lt": "enforced_at.lt",
}

QUERY_OPTIONS = {"sort": ["-enforced_at", "rule.ref"]}

FILTER_TRANSFORM_FUNCTIONS = {
    "enforced_at": lambda value: isotime.parse(value=value),
    "enforced_at_gt": lambda value: isotime.parse(value=value),
    "enforced_at_lt": lambda value: isotime.parse(value=value),
}


class RuleEnforcementController(ResourceController):

    model = RuleEnforcementAPI
    access = RuleEnforcement

    # ResourceController attributes
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
        return super(RuleEnforcementController, self)._get_all(
            exclude_fields=exclude_attributes,
            include_fields=include_attributes,
            sort=sort,
            offset=offset,
            limit=limit,
            raw_filters=raw_filters,
            requester_user=requester_user,
        )

    def get_one(self, id, requester_user):
        return super(RuleEnforcementController, self)._get_one_by_id(
            id,
            requester_user=requester_user,
            permission_type=PermissionType.RULE_ENFORCEMENT_VIEW,
        )


rule_enforcements_controller = RuleEnforcementController()
