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

from st2api.controllers.actions import ActionsController
from st2api.controllers.actionexecutions import ActionExecutionsController
from st2api.controllers.datastore import KeyValuePairController
from st2api.controllers.history import HistoryController
from st2api.controllers.rules import RuleController
from st2api.controllers.runnertypes import RunnerTypesController
from st2api.controllers.sensors import SensorTypeController
from st2api.controllers.triggers import TriggerTypeController, TriggerController, \
    TriggerInstanceController
from st2api.controllers.webhooks import WebhooksController


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
