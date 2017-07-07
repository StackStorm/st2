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

import os
import uuid

from st2common import log as logging
from st2common.runners.base import ActionRunner
from st2common.runners import python_action_wrapper

LOG = logging.getLogger(__name__)

__all__ = [
    'get_runner',
    'Inquirer',
]

# constants to lookup in runner_parameters.
RUNNER_SCHEMA = 'schema'

BASE_DIR = os.path.dirname(os.path.abspath(python_action_wrapper.__file__))


def get_runner():
    'RunnerTestCase',
    return Inquirer(str(uuid.uuid4()))


class Inquirer(ActionRunner):
    """ This runner is responsible for handling st2.ask actions (i.e. can return "pending" status)

    This approach gives safer access to setting execution status and examining data in context

    TODO
    - Should this runner also be written to handle an "st2.respond" action in addition to "st2.ask"?
    """

    def __init__(self, runner_id):
        super(Inquirer, self).__init__(runner_id=runner_id)

    def pre_run(self):
        super(Inquirer, self).pre_run()

        # TODO :This is awful, but the way "runner_parameters" and other variables get
        # assigned on the runner instance is even worse. Those arguments should
        # be passed to the constructor.
        self._schema = self.runner_parameters.get(RUNNER_SCHEMA, self._schema)

    def run(self, action_parameters):

        # 1 - Retrieve JSON schema from runner parameters

        # 2 - Retrieve response from execution context

        # 3 - Use the schema to validate response data

        # 4 - If valid, set status to success. If not valid, set status to pending.
        # Return this status as well as the entirety of data in context. I.e:
        return (status, context_data)
