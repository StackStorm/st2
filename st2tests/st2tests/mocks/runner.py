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

import json

from st2actions.runners import ActionRunner
from st2common.constants.action import (LIVEACTION_STATUS_SUCCEEDED)

__all__ = [
    'get_runner',
    'MockActionRunner'
]


def get_runner():
    return MockActionRunner()


class MockActionRunner(ActionRunner):
    def __init__(self):
        super(MockActionRunner, self).__init__(runner_id='1')

        self.pre_run_called = False
        self.run_called = False
        self.post_run_called = False

    def pre_run(self):
        super(MockActionRunner, self).pre_run()
        self.pre_run_called = True

    def run(self, action_params):
        self.run_called = True
        result = {}

        if self.runner_parameters.get('raise', False):
            raise Exception('Raise required.')

        default_result = {
            'ran': True,
            'action_params': action_params
        }
        default_context = {
            'third_party_system': {
                'ref_id': '1234'
            }
        }

        status = self.runner_parameters.get('mock_status', LIVEACTION_STATUS_SUCCEEDED)
        result = self.runner_parameters.get('mock_result', default_result)
        context = self.runner_parameters.get('mock_context', default_context)

        return (status, json.dumps(result), context)

    def post_run(self, status, result):
        self.post_run_called = True
