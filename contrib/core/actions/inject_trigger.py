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

from __future__ import absolute_import

from st2common.runners.base_action import Action
from st2common.database_setup import db_setup
from st2common.database_setup import db_teardown
from st2common.transport.bootstrap_utils import register_exchanges_with_retry
from st2common.services.trigger_dispatcher import BaseTriggerDispatcherService

__all__ = [
    'InjectTriggerAction'
]


class InjectTriggerAction(Action):
    """
    NOTE: Server where this action run needs to have access to the database.

    That's always the case right now, but if this assertion changes in the future, we should move
    to utilizing the API for dispatching a trigger.
    """

    def run(self, trigger, payload=None, trace_tag=None):
        payload = payload or {}

        # 1. Establish connection to the database
        db_setup()
        register_exchanges_with_retry()

        # 2. Dispatch the trigger
        try:
            service = BaseTriggerDispatcherService(logger=self.logger)
            return service.dispatch(trigger=trigger, payload=payload, trace_tag=trace_tag)
        finally:
            db_teardown()
