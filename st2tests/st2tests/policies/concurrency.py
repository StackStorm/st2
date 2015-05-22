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
from st2common.util import action_db as action_utils


class ConcurrencyPolicy(base.ResourcePolicy):

    def __init__(self, *args, **kwargs):
        super(ConcurrencyPolicy, self).__init__(*args, **kwargs)
        self.applied = False

    def get_threshold(self):
        return getattr(self, 'threshold', 0)

    def apply(self, target):
        self.applied = True

        if self.get_threshold() <= 0:
            # Cancel the action execution.
            target = action_utils.update_liveaction_status(
                status=action_constants.LIVEACTION_STATUS_CANCELED,
                liveaction_id=target.id,
                publish=False)

        return target
