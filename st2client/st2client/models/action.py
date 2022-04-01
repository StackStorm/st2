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

import logging

from st2client.models import core


LOG = logging.getLogger(__name__)


class RunnerType(core.Resource):
    _alias = "Runner"
    _display_name = "Runner"
    _plural = "RunnerTypes"
    _plural_display_name = "Runners"
    _repr_attributes = ["name", "enabled", "description"]


class Action(core.Resource):
    _plural = "Actions"
    _repr_attributes = ["name", "pack", "enabled", "runner_type"]
    _url_path = "actions"


class Execution(core.Resource):
    _alias = "Execution"
    _display_name = "Action Execution"
    _url_path = "executions"
    _plural = "ActionExecutions"
    _plural_display_name = "Action executions"
    _repr_attributes = [
        "status",
        "action",
        "start_timestamp",
        "end_timestamp",
        "parameters",
        "delay",
    ]


# NOTE: LiveAction has been deprecated in favor of Execution. It will be left here for
# backward compatibility reasons until v3.2.0
class LiveAction(Execution):
    pass
