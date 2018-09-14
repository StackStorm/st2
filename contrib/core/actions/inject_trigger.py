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

__all__ = [
    'InjectTriggerAction'
]


class InjectTriggerAction(Action):
    def run(self, trigger, payload=None, trace_tag=None):
        payload = payload or {}

        datastore_service = self.action_service.datastore_service
        client = datastore_service.get_api_client()

        # Dispatch the trigger using the /webhooks/st2 API endpoint
        # NOTE: Webhooks API endpoint is asynchronous so we don't know if the actual injection
        # results in a TriggerInstanceDB database object creation or not. The object is created
        # inside rulesengine service and could fail due to the user providing an invalid trigger
        # reference or similar.
        self.logger.debug('Injecting trigger "%s" with payload="%s"' % (trigger, str(payload)))
        result = client.webhooks.post_generic_webhook(trigger=trigger, payload=payload,
                                                      trace_tag=trace_tag)

        return result
