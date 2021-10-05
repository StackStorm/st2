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

try:
    import simplejson as json
except:
    import json

from st2common.runners.base import AsyncActionRunner
from st2common.constants.action import LIVEACTION_STATUS_RUNNING

RAISE_PROPERTY = "raise"


def get_runner():
    return AsyncTestRunner()


class AsyncTestRunner(AsyncActionRunner):
    def __init__(self):
        super(AsyncTestRunner, self).__init__(runner_id="1")
        self.pre_run_called = False
        self.run_called = False
        self.post_run_called = False

    def pre_run(self):
        self.pre_run_called = True

    def run(self, action_params):
        self.run_called = True
        result = {}
        if self.runner_parameters.get(RAISE_PROPERTY, False):
            raise Exception("Raise required.")
        else:
            result = {"ran": True, "action_params": action_params}

        return (LIVEACTION_STATUS_RUNNING, json.dumps(result), {"id": "foo"})

    def post_run(self, status, result):
        self.post_run_called = True
