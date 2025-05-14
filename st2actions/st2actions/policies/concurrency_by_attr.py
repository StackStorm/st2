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
from st2common import log as logging
from st2common.fields import JSONDictEscapedFieldCompatibilityField
from st2common.persistence import action as action_access
from st2common.services import action as action_service
from st2common.policies.concurrency import BaseConcurrencyApplicator
from st2common.services import coordination

__all__ = ["ConcurrencyByAttributeApplicator"]

LOG = logging.getLogger(__name__)


class ConcurrencyByAttributeApplicator(BaseConcurrencyApplicator):
    def __init__(
        self, policy_ref, policy_type, threshold=0, action="delay", attributes=None
    ):
        super(ConcurrencyByAttributeApplicator, self).__init__(
            policy_ref=policy_ref,
            policy_type=policy_type,
            threshold=threshold,
            action=action,
        )
        self.attributes = attributes or []

    def _apply_before(self, target):

        scheduled_filters = {
            "status": action_constants.LIVEACTION_STATUS_SCHEDULED,
            "action": target.action,
        }
        scheduled = [i for i in action_access.LiveAction.query(**scheduled_filters)]

        running_filters = {
            "status": action_constants.LIVEACTION_STATUS_RUNNING,
            "action": target.action,
        }
        running = [i for i in action_access.LiveAction.query(**running_filters)]
        running.extend(scheduled)
        count = 0
        target_parameters = JSONDictEscapedFieldCompatibilityField().parse_field_value(
            target.parameters
        )
        target_key_value_policy_attributes = {
            k: v for k, v in target_parameters.items() if k in self.attributes
        }

        for i in running:
            running_event_parameters = (
                JSONDictEscapedFieldCompatibilityField().parse_field_value(i.parameters)
            )
            # list of event parameter values that are also in policy
            running_event_policy_item_key_value_attributes = {
                k: v
                for k, v in running_event_parameters.items()
                if k in self.attributes
            }
            if (
                running_event_policy_item_key_value_attributes
                == target_key_value_policy_attributes
            ):
                count += 1

        # Mark the execution as scheduled if threshold is not reached or delayed otherwise.
        if count < self.threshold:
            LOG.debug(
                "There are %s instances of %s in scheduled or running status. "
                "Threshold of %s is not reached. Action execution will be scheduled.",
                count,
                target.action,
                self._policy_ref,
            )
            status = action_constants.LIVEACTION_STATUS_REQUESTED
        else:
            action = "delayed" if self.policy_action == "delay" else "canceled"
            LOG.debug(
                "There are %s instances of %s in scheduled or running status. "
                "Threshold of %s is reached. Action execution will be %s.",
                count,
                target.action,
                self._policy_ref,
                action,
            )
            status = self._get_status_for_policy_action(action=self.policy_action)

        # Update the status in the database. Publish status for cancellation so the
        # appropriate runner can cancel the execution. Other statuses are not published
        # because they will be picked up by the worker(s) to be processed again,
        # leading to duplicate action executions.
        publish = status == action_constants.LIVEACTION_STATUS_CANCELING
        target = action_service.update_status(target, status, publish=publish)

        return target

    def apply_before(self, target):
        target = super(ConcurrencyByAttributeApplicator, self).apply_before(
            target=target
        )

        valid_states = [
            action_constants.LIVEACTION_STATUS_REQUESTED,
            action_constants.LIVEACTION_STATUS_DELAYED,
        ]

        # Exit if target not in valid state.
        if target.status not in valid_states:
            LOG.debug(
                "The live action is not schedulable therefore the policy "
                '"%s" cannot be applied. %s',
                self._policy_ref,
                target,
            )
            return target

        # Warn users that the coordination service is not configured.
        if not coordination.configured():
            LOG.warning(
                "Coordination service is not configured. Policy enforcement is best effort."
            )

        target = self._apply_before(target)

        return target
