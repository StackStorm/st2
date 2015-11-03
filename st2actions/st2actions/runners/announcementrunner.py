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

from st2actions.runners import ActionRunner
from st2common import log as logging
from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED
from st2common.transport.announcement import AnnouncementDispatcher

LOG = logging.getLogger(__name__)


def get_runner():
    return AnnouncementRunner(str(uuid.uuid4()))


class AnnouncementRunner(ActionRunner):
    def __init__(self, runner_id):
        super(AnnouncementRunner, self).__init__(runner_id=runner_id)
        self._dispatcher = AnnouncementDispatcher(LOG)

    def pre_run(self):
        LOG.debug('Entering AnnouncementRunner.pre_run() for liveaction_id="%s"',
                  self.liveaction_id)

    def run(self, action_parameters):
        self._dispatcher.dispatch('general', payload=action_parameters)
        return (LIVEACTION_STATUS_SUCCEEDED, {'OK': True}, None)
