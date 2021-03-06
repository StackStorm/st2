# -*- coding: utf-8 -*-

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
import json

from integration.orquesta import base
from six.moves import range

from st2common.constants import action as ac_const


class WiringTest(base.TestWorkflowExecution):
    def test_concurrent_load(self):
        load_count = 3
        delay_poll = load_count * 5

        wf_name = "examples.orquesta-mock-create-vm"
        wf_input = {"vm_name": "demo1", "meta": {"demo1.itests.org": "10.3.41.99"}}
        exs = [self._execute_workflow(wf_name, wf_input) for i in range(load_count)]

        eventlet.sleep(delay_poll)

        for ex in exs:
            e = self._wait_for_completion(ex)
            self.assertEqual(
                e.status, ac_const.LIVEACTION_STATUS_SUCCEEDED, json.dumps(e.result)
            )
            self.assertIn("output", e.result)
            self.assertIn("vm_id", e.result["output"])

    def test_with_items_load(self):
        wf_name = "examples.orquesta-with-items-concurrency"

        num_items = 10
        concurrency = 10
        members = [str(i).zfill(5) for i in range(0, num_items)]
        wf_input = {"members": members, "concurrency": concurrency}

        message = "%s, resistance is futile!"
        expected_output = {"items": [message % i for i in members]}
        expected_result = {"output": expected_output}

        ex = self._execute_workflow(wf_name, wf_input)
        ex = self._wait_for_completion(ex)

        self.assertEqual(ex.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        self.assertDictEqual(ex.result, expected_result)
