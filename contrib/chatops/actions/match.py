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

import os

from st2common.runners.base_action import Action
from st2client.models.action_alias import ActionAliasMatch
from st2client.client import Client


class MatchAction(Action):
    def __init__(self, config=None):
        super(MatchAction, self).__init__(config=config)
        api_url = os.environ.get("ST2_ACTION_API_URL", None)
        token = os.environ.get("ST2_ACTION_AUTH_TOKEN", None)
        self.client = Client(api_url=api_url, token=token)

    def run(self, text):
        alias_match = ActionAliasMatch()
        alias_match.command = text
        matches = self.client.managers["ActionAlias"].match(alias_match)
        return {"alias": _format_match(matches[0]), "representation": matches[1]}


def _format_match(match):
    return {"name": match.name, "pack": match.pack, "action_ref": match.action_ref}
