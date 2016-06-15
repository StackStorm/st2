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

from st2api.controllers.v1.actions import ActionsController
from st2api.controllers.v1.actionalias import ActionAliasController
from st2api.controllers.v1.actionexecutions import ActionExecutionsController
from st2api.controllers.v1.aliasexecution import ActionAliasExecutionController
from st2api.controllers.v1.auth import ApiKeyController
from st2api.controllers.v1.keyvalue import KeyValuePairController
from st2api.controllers.v1.packs import PacksController
from st2api.controllers.v1.pack_config_schemas import PackConfigSchemasController
from st2api.controllers.v1.pack_configs import PackConfigsController
from st2api.controllers.v1.policies import PolicyTypeController, PolicyController
from st2api.controllers.v1.ruletypes import RuleTypesController
from st2api.controllers.v1.rules import RuleController
from st2api.controllers.v1.rule_enforcements import RuleEnforcementController
from st2api.controllers.v1.runnertypes import RunnerTypesController
from st2api.controllers.v1.sensors import SensorTypeController
from st2api.controllers.v1.traces import TracesController
from st2api.controllers.v1.triggers import TriggerTypeController, TriggerController, \
    TriggerInstanceController
from st2api.controllers.v1.webhooks import WebhooksController
from st2api.controllers.v1.rbac import RBACController

__all__ = [
    'RootController'
]


class RootController(object):
    # Pack related controllers
    packs = PacksController()
    config_schemas = PackConfigSchemasController()
    configs = PackConfigsController()

    actions = ActionsController()
    actionexecutions = ActionExecutionsController()
    executions = actionexecutions  # We should deprecate actionexecutions.
    policies = PolicyController()
    policytypes = PolicyTypeController()
    runnertypes = RunnerTypesController()
    sensortypes = SensorTypeController()
    triggertypes = TriggerTypeController()
    triggers = TriggerController()
    triggerinstances = TriggerInstanceController()
    ruletypes = RuleTypesController()
    rules = RuleController()
    ruleenforcements = RuleEnforcementController()
    keys = KeyValuePairController()
    webhooks = WebhooksController()
    actionalias = ActionAliasController()
    aliasexecution = ActionAliasExecutionController()
    traces = TracesController()
    rbac = RBACController()
    apikeys = ApiKeyController()
