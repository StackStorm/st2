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

from st2client.client import Client
from st2client.models.keyvalue import KeyValuePair  # pylint: disable=no-name-in-module
from st2common.runners.base_action import Action

__all__ = ["St2RegisterAction"]

COMPATIBILITY_TRANSFORMATIONS = {
    "runners": "runner",
    "triggers": "trigger",
    "sensors": "sensor",
    "actions": "action",
    "rules": "rule",
    "rule_types": "rule_type",
    "aliases": "alias",
    "policiy_types": "policy_type",
    "policies": "policy",
    "configs": "config",
}


def filter_none_values(value):
    """
    Filter out string "None" values from the provided dict.
    :rtype: ``dict``
    """
    result = dict([(k, v) for k, v in value.items() if v != "None"])
    return result


def format_result(item):
    if not item:
        return None

    return item.to_dict()


class St2RegisterAction(Action):
    def __init__(self, config):
        super(St2RegisterAction, self).__init__(config)
        self._client = Client
        self._kvp = KeyValuePair
        self.client = self._get_client()

    def run(self, register, packs=None):
        types = []

        for type in register.split(","):
            if type in COMPATIBILITY_TRANSFORMATIONS:
                types.append(COMPATIBILITY_TRANSFORMATIONS[type])
            else:
                types.append(type)

        method_kwargs = {"types": types}

        packs.reverse()
        if packs:
            method_kwargs["packs"] = packs

        result = self._run_client_method(
            method=self.client.packs.register,
            method_kwargs=method_kwargs,
            format_func=format_result,
        )
        # TODO: make sure to return proper model
        return result

    def _get_client(self):
        base_url, api_url, auth_url = self._get_st2_urls()
        token = self._get_auth_token()
        cacert = self._get_cacert()

        client_kwargs = {}
        if cacert:
            client_kwargs["cacert"] = cacert

        return self._client(
            base_url=base_url,
            api_url=api_url,
            auth_url=auth_url,
            token=token,
            **client_kwargs,
        )

    def _get_st2_urls(self):
        # First try to use base_url from config.
        base_url = self.config.get("base_url", None)
        api_url = self.config.get("api_url", None)
        auth_url = self.config.get("auth_url", None)

        # not found look up from env vars. Assuming the pack is
        # configuered to work with current StackStorm instance.
        if not base_url:
            api_url = os.environ.get("ST2_ACTION_API_URL", None)
            auth_url = os.environ.get("ST2_ACTION_AUTH_URL", None)

        return base_url, api_url, auth_url

    def _get_auth_token(self):
        # First try to use auth_token from config.
        token = self.config.get("auth_token", None)

        # not found look up from env vars. Assuming the pack is
        # configuered to work with current StackStorm instance.
        if not token:
            token = os.environ.get("ST2_ACTION_AUTH_TOKEN", None)

        return token

    def _get_cacert(self):
        cacert = self.config.get("cacert", None)
        return cacert

    def _run_client_method(
        self, method, method_kwargs, format_func, format_kwargs=None
    ):
        """
        Run the provided client method and format the result.

        :param method: Client method to run.
        :type method: ``func``

        :param method_kwargs: Keyword arguments passed to the client method.
        :type method_kwargs: ``dict``

        :param format_func: Function for formatting the result.
        :type format_func: ``func``

        :rtype: ``list`` of ``dict``
        """
        # Filter out parameters with string value of "None"
        # This is a work around since the default values can only be strings
        method_kwargs = filter_none_values(method_kwargs)
        method_name = method.__name__
        self.logger.debug(
            'Calling client method "%s" with kwargs "%s"' % (method_name, method_kwargs)
        )

        result = method(**method_kwargs)
        result = format_func(result, **format_kwargs or {})
        return result
