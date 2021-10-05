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

import six
import os

from st2common.runners.base_action import Action
from st2client.client import Client
from st2common.util import jinja as jinja_utils


class FormatResultAction(Action):
    def __init__(self, config=None, action_service=None):
        super(FormatResultAction, self).__init__(
            config=config, action_service=action_service
        )
        api_url = os.environ.get("ST2_ACTION_API_URL", None)
        token = os.environ.get("ST2_ACTION_AUTH_TOKEN", None)
        self.client = Client(api_url=api_url, token=token)
        self.jinja = jinja_utils.get_jinja_environment(allow_undefined=True)
        self.jinja.tests["in"] = lambda item, list: item in list

        path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(path, "templates/default.j2"), "r") as f:
            self.default_template = f.read()

    def run(self, execution_id):
        execution = self._get_execution(execution_id)
        context = {"six": six, "execution": execution}
        template = self.default_template
        result = {"enabled": True}

        alias_id = execution["context"].get("action_alias_ref", {}).get("id", None)
        if alias_id:
            alias = self.client.managers["ActionAlias"].get_by_id(alias_id)

            context.update({"alias": alias})

            result_params = getattr(alias, "result", None)
            if result_params:
                if not result_params.get("enabled", True):
                    result["enabled"] = False
                else:
                    if "format" in alias.result:
                        template = alias.result["format"]
                    if "extra" in alias.result:
                        result["extra"] = jinja_utils.render_values(
                            alias.result["extra"], context
                        )

        result["message"] = self.jinja.from_string(template).render(context)

        return result

    def _get_execution(self, execution_id):
        if not execution_id:
            raise ValueError("Invalid execution_id provided.")
        execution = self.client.liveactions.get_by_id(id=execution_id)
        if not execution:
            return None
        excludes = ["trigger", "trigger_type", "trigger_instance", "liveaction"]
        return execution.to_dict(exclude_attributes=excludes)
