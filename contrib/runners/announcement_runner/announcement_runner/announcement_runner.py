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
import uuid

from st2common.runners.base import ActionRunner
from st2common.runners.base import get_metadata as get_runner_metadata
from st2common import log as logging
from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED
from st2common.exceptions import actionrunner as runnerexceptions
from st2common.models.api.trace import TraceContext
from st2common.transport.announcement import AnnouncementDispatcher

__all__ = ["AnnouncementRunner", "get_runner", "get_metadata"]

LOG = logging.getLogger(__name__)


class AnnouncementRunner(ActionRunner):
    def __init__(self, runner_id):
        super(AnnouncementRunner, self).__init__(runner_id=runner_id)
        self._dispatcher = AnnouncementDispatcher(LOG)

    def pre_run(self):
        super(AnnouncementRunner, self).pre_run()

        LOG.debug(
            'Entering AnnouncementRunner.pre_run() for liveaction_id="%s"',
            self.liveaction_id,
        )

        if not self.runner_parameters.get("experimental"):
            message = "Experimental flag is missing for action %s" % self.action.ref
            LOG.exception("Experimental runner is called without experimental flag.")
            raise runnerexceptions.ActionRunnerPreRunError(message)

        self._route = self.runner_parameters.get("route")

    def run(self, action_parameters):
        trace_context = self.liveaction.context.get("trace_context", None)
        if trace_context:
            trace_context = TraceContext(**trace_context)

        self._dispatcher.dispatch(
            self._route, payload=action_parameters, trace_context=trace_context
        )

        result = {"output": action_parameters}
        result.update(action_parameters)

        return (LIVEACTION_STATUS_SUCCEEDED, result, None)


def get_runner():
    return AnnouncementRunner(str(uuid.uuid4()))


def get_metadata():
    return get_runner_metadata("announcement_runner")[0]
