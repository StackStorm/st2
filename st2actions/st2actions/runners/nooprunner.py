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

import uuid
from st2common import log as logging
from st2actions.runners import ActionRunner
from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED
import st2common.util.jsonify as jsonify

LOG = logging.getLogger(__name__)

__all__ = [
    'get_runner'
]


def get_runner():
    return NoopRunner(str(uuid.uuid4()))


class NoopRunner(ActionRunner):
    """
    Runner which does absolutely nothing. No-op action.
    """
    KEYS_TO_TRANSFORM = ['stdout', 'stderr']

    def __init__(self, runner_id):
        super(NoopRunner, self).__init__(runner_id=runner_id)

    def pre_run(self):
        super(NoopRunner, self).pre_run()

    def run(self, action_parameters):

        LOG.info('Executing action via NoopRunner: %s', self.runner_id)
        LOG.info('[Action info] name: %s, Id: %s',
                 self.action_name, str(self.execution_id))

        result = {
            'failed': False,
            'succeeded': True,
            'return_code': 0,
        }

        status = LIVEACTION_STATUS_SUCCEEDED
        return (status, jsonify.json_loads(result, NoopRunner.KEYS_TO_TRANSFORM), None)
