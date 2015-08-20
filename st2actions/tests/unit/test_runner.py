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

try:
    import simplejson as json
except:
    import json

from st2actions.runners import ActionRunner
from st2common.constants.action import (LIVEACTION_STATUS_SUCCEEDED)

RAISE_PROPERTY = 'raise'


def get_runner():
    return TestRunner()


class TestRunner(ActionRunner):
    def __init__(self):
        super(TestRunner, self).__init__(runner_id='1')
        self.pre_run_called = False
        self.run_called = False
        self.post_run_called = False

    def pre_run(self):
        self.pre_run_called = True

    def run(self, action_params):
        self.run_called = True
        result = {}
        if self.runner_parameters.get(RAISE_PROPERTY, False):
            raise Exception('Raise required.')
        else:
            result = {
                'ran': True,
                'action_params': action_params
            }
        context = {
            'third_party_system': {
                'ref_id': '1234'
            }
        }

        return (LIVEACTION_STATUS_SUCCEEDED, json.dumps(result), context)

    def post_run(self, status, result):
        self.post_run_called = True
