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

from st2client.models import core

__all__ = ["ActionAlias", "ActionAliasMatch"]


class ActionAlias(core.Resource):
    _alias = "Action-Alias"
    _display_name = "Action Alias"
    _plural = "ActionAliases"
    _plural_display_name = "Action Aliases"
    _url_path = "actionalias"
    _repr_attributes = ["name", "pack", "action_ref"]


class ActionAliasMatch(core.Resource):
    _alias = "Action-Alias-Match"
    _display_name = "ActionAlias Match"
    _plural = "ActionAliasMatches"
    _plural_display_name = "Action Alias Matches"
    _url_path = "actionalias"
    _repr_attributes = ["command"]
