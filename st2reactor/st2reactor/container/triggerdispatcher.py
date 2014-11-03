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

import datetime

from st2common import log as logging
import st2reactor.container.utils as container_utils
from st2reactor.rules.engine import RulesEngine

LOG = logging.getLogger('st2reactor.sensor.dispatcher')


class TriggerDispatcher(object):

    def __init__(self):
        self.rules_engine = RulesEngine()

    def dispatch(self, trigger, payload=None):
        """
        """
        trigger_instance = container_utils.create_trigger_instance(
            trigger,
            payload or {},
            datetime.datetime.utcnow())

        if trigger_instance:
            self.rules_engine.handle_trigger_instance(trigger_instance)
