# -*- coding: utf-8 -*-
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import logging

from st2client import models
from st2client.models import reactor
from st2client.models import action


LOG = logging.getLogger(__name__)


class Client(object):

    def __init__(self, endpoints):
        self.actions = models.ResourceManager(
            action.Action, endpoints['action'])
        self.executions = models.ResourceManager(
            action.ActionExecution, endpoints['action'])
        self.rules = models.ResourceManager(
            reactor.Rule, endpoints['reactor'])
        self.triggers = models.ResourceManager(
            reactor.Trigger, endpoints['reactor'], read_only=True)
