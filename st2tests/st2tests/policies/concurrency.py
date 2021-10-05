# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
from st2common.constants import action as action_constants
from st2common.util import action_db as action_utils
from st2actions.policies.concurrency import BaseConcurrencyApplicator


class FakeConcurrencyApplicator(BaseConcurrencyApplicator):
    def __init__(self, policy_ref, policy_type, *args, **kwargs):
        super(FakeConcurrencyApplicator, self).__init__(
            policy_ref=policy_ref,
            policy_type=policy_type,
            threshold=kwargs.get("threshold", 0),
        )

    def get_threshold(self):
        return self.threshold

    def apply_before(self, target):
        if self.get_threshold() <= 0:
            # Cancel the action execution.
            target = action_utils.update_liveaction_status(
                status=action_constants.LIVEACTION_STATUS_CANCELED,
                liveaction_id=target.id,
                publish=False,
            )

        return target

    def apply_after(self, target):
        return target
