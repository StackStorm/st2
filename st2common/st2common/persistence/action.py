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
from st2common.models.db.action import action_access
from st2common.persistence import base as persistence
from st2common.persistence.actionalias import ActionAlias
from st2common.persistence.execution import ActionExecution
from st2common.persistence.executionstate import ActionExecutionState
from st2common.persistence.liveaction import LiveAction
from st2common.persistence.runner import RunnerType

__all__ = [
    "Action",
    "ActionAlias",
    "ActionExecution",
    "ActionExecutionState",
    "LiveAction",
    "RunnerType",
]


class Action(persistence.ContentPackResource):
    impl = action_access

    @classmethod
    def _get_impl(cls):
        return cls.impl
