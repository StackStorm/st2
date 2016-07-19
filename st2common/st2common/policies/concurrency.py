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

from st2common.constants import action as action_constants
from st2common.policies import base
from st2common.services import coordination

__all__ = [
    'BaseConcurrencyApplicator'
]


class BaseConcurrencyApplicator(base.ResourcePolicyApplicator):
    def __init__(self, policy_ref, policy_type, threshold=0, action='delay'):
        super(BaseConcurrencyApplicator, self).__init__(policy_ref=policy_ref,
                                                        policy_type=policy_type)
        self.threshold = threshold
        self.policy_action = action

        self.coordinator = coordination.get_coordinator()

    def _get_status_for_policy_action(self, action):
        if action == 'delay':
            status = action_constants.LIVEACTION_STATUS_DELAYED
        elif action == 'cancel':
            status = action_constants.LIVEACTION_STATUS_CANCELED

        return status
