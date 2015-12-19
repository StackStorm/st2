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

import six

from st2common import log as logging
from st2api.controllers import resource
from st2common.models.api.base import jsexpose
from st2common.models.api.rule_enforcement import RuleEnforcementAPI
from st2common.persistence.rule_enforcement import RuleEnforcement
from st2common.rbac.decorators import request_user_has_permission
from st2common.rbac.decorators import request_user_has_resource_db_permission
from st2common.rbac.types import PermissionType
from st2common.util import isotime


http_client = six.moves.http_client

LOG = logging.getLogger(__name__)


SUPPORTED_FILTERS = {
    'rule_ref': 'rule.ref',
    'rule_id': 'rule.id',
    'execution': 'execution_id',
    'trigger_instance': 'trigger_instance_id',
    'enforced_at': 'enforced_at',
    'enforced_at_gt': 'enforced_at.gt',
    'enforced_at_lt': 'enforced_at.lt'
}


class RuleEnforcementController(resource.ResourceController):

    model = RuleEnforcementAPI
    access = RuleEnforcement

    # ResourceController attributes
    query_options = {
        'sort': ['-enforced_at', 'rule.ref']
    }

    supported_filters = SUPPORTED_FILTERS
    filter_transform_functions = {
        'enforced_at': lambda value: isotime.parse(value=value),
        'enforced_at_gt': lambda value: isotime.parse(value=value),
        'enforced_at_lt': lambda value: isotime.parse(value=value)
    }

    @request_user_has_permission(permission_type=PermissionType.RULE_ENFORCEMENT_LIST)
    @jsexpose()
    def get_all(self, **kwargs):
        return super(RuleEnforcementController, self)._get_all(**kwargs)

    @request_user_has_resource_db_permission(permission_type=PermissionType.RULE_ENFORCEMENT_VIEW)
    @jsexpose(arg_types=[str])
    def get_one(self, ref_or_id):
        return super(RuleEnforcementController, self)._get_one(ref_or_id)
