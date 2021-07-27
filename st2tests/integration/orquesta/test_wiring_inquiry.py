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

import eventlet

from integration.orquesta import base

from st2common.constants import action as ac_const


class InquiryWiringTest(base.TestWorkflowExecution):
    def test_basic_inquiry(self):
        # Launch the workflow. The workflow will paused at the pending task.
        ex = self._execute_workflow("examples.orquesta-ask-basic")
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_PAUSED)

        # Respond to the inquiry.
        ac_exs = self._wait_for_task(
            ex, "get_approval", ac_const.LIVEACTION_STATUS_PENDING
        )
        self.st2client.inquiries.respond(ac_exs[0].id, {"approved": True})

        # Wait for completion.
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_SUCCEEDED)

    def test_consecutive_inquiries(self):
        # Launch the workflow. The workflow will paused at the pending task.
        ex = self._execute_workflow("examples.orquesta-ask-consecutive")
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_PAUSED)

        # Respond to the first inquiry.
        t1_ac_exs = self._wait_for_task(
            ex, "get_approval", ac_const.LIVEACTION_STATUS_PENDING
        )
        self.st2client.inquiries.respond(t1_ac_exs[0].id, {"approved": True})

        # Wait for the workflow to pause again.
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_PAUSED)

        # Respond to the second inquiry.
        t2_ac_exs = self._wait_for_task(
            ex, "get_confirmation", ac_const.LIVEACTION_STATUS_PENDING
        )
        self.st2client.inquiries.respond(t2_ac_exs[0].id, {"approved": True})

        # Wait for completion.
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_SUCCEEDED)

    def test_parallel_inquiries(self):
        # Launch the workflow. The workflow will paused at the pending task.
        ex = self._execute_workflow("examples.orquesta-ask-parallel")
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_PAUSED)

        # Respond to the first inquiry.
        t1_ac_exs = self._wait_for_task(
            ex, "ask_jack", ac_const.LIVEACTION_STATUS_PENDING
        )
        self.st2client.inquiries.respond(t1_ac_exs[0].id, {"approved": True})
        t1_ac_exs = self._wait_for_task(
            ex, "ask_jack", ac_const.LIVEACTION_STATUS_SUCCEEDED
        )

        # Allow some time for the first inquiry to get processed.
        eventlet.sleep(2)

        # Respond to the second inquiry.
        t2_ac_exs = self._wait_for_task(
            ex, "ask_jill", ac_const.LIVEACTION_STATUS_PENDING
        )
        self.st2client.inquiries.respond(t2_ac_exs[0].id, {"approved": True})
        t2_ac_exs = self._wait_for_task(
            ex, "ask_jill", ac_const.LIVEACTION_STATUS_SUCCEEDED
        )

        # Wait for completion.
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_SUCCEEDED)

    def test_nested_inquiry(self):
        # Launch the workflow. The workflow will paused at the pending task.
        ex = self._execute_workflow("examples.orquesta-ask-nested")
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_PAUSED)

        # Get the action execution of the subworkflow
        ac_exs = self._wait_for_task(
            ex, "get_approval", ac_const.LIVEACTION_STATUS_PAUSED
        )

        # Respond to the inquiry in the subworkflow.
        t2_t2_ac_exs = self._wait_for_task(
            ac_exs[0], "get_approval", ac_const.LIVEACTION_STATUS_PENDING
        )

        self.st2client.inquiries.respond(t2_t2_ac_exs[0].id, {"approved": True})

        # Wait for completion.
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_SUCCEEDED)
