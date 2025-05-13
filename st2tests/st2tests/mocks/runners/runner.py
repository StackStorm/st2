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
import json

from st2common.runners.base import ActionRunner
from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED

__all__ = ["get_runner", "MockActionRunner"]


def get_runner(config=None):
    return MockActionRunner()


class MockActionRunner(ActionRunner):
    def __init__(self):
        super(MockActionRunner, self).__init__(runner_id="1")
        self.pre_run_called = False
        self.run_called = False
        self.post_run_called = False

    def pre_run(self):
        super(MockActionRunner, self).pre_run()
        self.pre_run_called = True

    def run(self, action_params):
        self.run_called = True
        result = {}

        if self.runner_parameters.get("raise", False):
            raise Exception("Raise required.")

        default_result = {
            "ran": True,
            "action_params": action_params,
            "failed": False,
            "stdout": "res",
            "stderr": "",
            "succeeded": True,
        }
        if action_params.get("actionstr", "") == "dict_resp":
            default_result["stdout"] = {"key": "value", "key2": {"sk1": "v1"}}

        default_context = {"third_party_system": {"ref_id": "1234"}}

        status = self.runner_parameters.get("mock_status", LIVEACTION_STATUS_SUCCEEDED)
        result = self.runner_parameters.get("mock_result", default_result)
        context = self.runner_parameters.get("mock_context", default_context)

        return (status, json.dumps(result), context)

    def post_run(self, status, result):
        super(MockActionRunner, self).post_run(status=status, result=result)
        self.post_run_called = True
