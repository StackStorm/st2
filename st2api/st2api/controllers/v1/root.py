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

from pecan import expose

from st2api.controllers.v1.actions import ActionsController
from st2api.controllers.v1.actionexecutions import ActionExecutionsController
from st2api.controllers.v1.datastore import KeyValuePairController
from st2api.controllers.v1.history import HistoryController
from st2api.controllers.v1.rules import RuleController
from st2api.controllers.v1.runnertypes import RunnerTypesController
from st2api.controllers.v1.sensors import SensorTypeController
from st2api.controllers.v1.triggers import TriggerTypeController, TriggerController, \
    TriggerInstanceController
from st2api.controllers.v1.webhooks import WebhooksController


class RootController(object):
    actions = ActionsController()
    actionexecutions = ActionExecutionsController()
    runnertypes = RunnerTypesController()
    sensortypes = SensorTypeController()
    triggertypes = TriggerTypeController()
    triggers = TriggerController()
    triggerinstances = TriggerInstanceController()
    rules = RuleController()
    keys = KeyValuePairController()
    history = HistoryController()
    webhooks = WebhooksController()

    @expose(generic=True, template='index.html')
    def index(self):
        return dict()
