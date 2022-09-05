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

import os
import logging
import warnings

import six

from st2client import models
from st2client.utils import httpclient
from st2client.models.core import ResourceManager
from st2client.models.core import ActionAliasResourceManager
from st2client.models.core import ActionAliasExecutionManager
from st2client.models.core import ActionResourceManager
from st2client.models.core import ExecutionResourceManager
from st2client.models.core import InquiryResourceManager
from st2client.models.core import TriggerInstanceResourceManager
from st2client.models.core import PackResourceManager
from st2client.models.core import ConfigManager
from st2client.models.core import WebhookManager
from st2client.models.core import StreamManager
from st2client.models.core import WorkflowManager
from st2client.models.core import ServiceRegistryGroupsManager
from st2client.models.core import ServiceRegistryMembersManager
from st2client.models.core import add_auth_token_to_kwargs_from_env
from st2client.models.core import KeyValuePairResourceManager


LOG = logging.getLogger(__name__)

# Default values for the options not explicitly specified by the user
DEFAULT_API_PORT = 9101
DEFAULT_AUTH_PORT = 9100
DEFAULT_STREAM_PORT = 9102

DEFAULT_BASE_URL = "http://127.0.0.1"
DEFAULT_API_VERSION = "v1"


class Client(object):
    def __init__(
        self,
        base_url=None,
        auth_url=None,
        api_url=None,
        stream_url=None,
        api_version=None,
        cacert=None,
        debug=False,
        token=None,
        api_key=None,
        basic_auth=None,
    ):
        # Get CLI options. If not given, then try to get it from the environment.
        self.endpoints = dict()

        # Populate the endpoints
        if base_url:
            self.endpoints["base"] = base_url
        else:
            self.endpoints["base"] = os.environ.get("ST2_BASE_URL", DEFAULT_BASE_URL)

        api_version = api_version or os.environ.get(
            "ST2_API_VERSION", DEFAULT_API_VERSION
        )

        self.endpoints["exp"] = "%s:%s/%s" % (
            self.endpoints["base"],
            DEFAULT_API_PORT,
            "exp",
        )

        if api_url:
            self.endpoints["api"] = api_url
        else:
            self.endpoints["api"] = os.environ.get(
                "ST2_API_URL",
                "%s:%s/%s" % (self.endpoints["base"], DEFAULT_API_PORT, api_version),
            )

        if auth_url:
            self.endpoints["auth"] = auth_url
        else:
            self.endpoints["auth"] = os.environ.get(
                "ST2_AUTH_URL", "%s:%s" % (self.endpoints["base"], DEFAULT_AUTH_PORT)
            )

        if stream_url:
            self.endpoints["stream"] = stream_url
        else:
            self.endpoints["stream"] = os.environ.get(
                "ST2_STREAM_URL",
                "%s:%s/%s" % (self.endpoints["base"], DEFAULT_STREAM_PORT, api_version),
            )

        if cacert is not None:
            self.cacert = cacert
        else:
            self.cacert = os.environ.get("ST2_CACERT", None)

        # Note: boolean is also a valid value for "cacert"
        is_cacert_string = isinstance(self.cacert, six.string_types)
        if self.cacert and is_cacert_string and not os.path.isfile(self.cacert):
            raise ValueError('CA cert file "%s" does not exist.' % (self.cacert))

        self.debug = debug

        # Note: This is a nasty hack for now, but we need to get rid of the decrator abuse
        if token:
            os.environ["ST2_AUTH_TOKEN"] = token

        self.token = token

        if api_key:
            os.environ["ST2_API_KEY"] = api_key

        self.api_key = api_key

        if basic_auth:
            # NOTE: We assume username can't contain colons
            if len(basic_auth.split(":", 1)) != 2:
                raise ValueError(
                    "basic_auth config options needs to be in the "
                    "username:password notation"
                )

            self.basic_auth = tuple(basic_auth.split(":", 1))
        else:
            self.basic_auth = None

        # Instantiate resource managers and assign appropriate API endpoint.
        self.managers = dict()
        self.managers["Token"] = ResourceManager(
            models.Token,
            self.endpoints["auth"],
            cacert=self.cacert,
            debug=self.debug,
            basic_auth=self.basic_auth,
        )
        self.managers["RunnerType"] = ResourceManager(
            models.RunnerType,
            self.endpoints["api"],
            cacert=self.cacert,
            debug=self.debug,
            basic_auth=self.basic_auth,
        )
        self.managers["Action"] = ActionResourceManager(
            models.Action,
            self.endpoints["api"],
            cacert=self.cacert,
            debug=self.debug,
            basic_auth=self.basic_auth,
        )
        self.managers["ActionAlias"] = ActionAliasResourceManager(
            models.ActionAlias,
            self.endpoints["api"],
            cacert=self.cacert,
            debug=self.debug,
            basic_auth=self.basic_auth,
        )
        self.managers["ActionAliasExecution"] = ActionAliasExecutionManager(
            models.ActionAliasExecution,
            self.endpoints["api"],
            cacert=self.cacert,
            debug=self.debug,
            basic_auth=self.basic_auth,
        )
        self.managers["ApiKey"] = ResourceManager(
            models.ApiKey,
            self.endpoints["api"],
            cacert=self.cacert,
            debug=self.debug,
            basic_auth=self.basic_auth,
        )
        self.managers["Config"] = ConfigManager(
            models.Config,
            self.endpoints["api"],
            cacert=self.cacert,
            debug=self.debug,
            basic_auth=self.basic_auth,
        )
        self.managers["ConfigSchema"] = ResourceManager(
            models.ConfigSchema,
            self.endpoints["api"],
            cacert=self.cacert,
            debug=self.debug,
            basic_auth=self.basic_auth,
        )
        self.managers["Execution"] = ExecutionResourceManager(
            models.Execution,
            self.endpoints["api"],
            cacert=self.cacert,
            debug=self.debug,
            basic_auth=self.basic_auth,
        )
        # NOTE: LiveAction has been deprecated in favor of Execution. It will be left here for
        # backward compatibility reasons until v3.2.0
        self.managers["LiveAction"] = self.managers["Execution"]
        self.managers["Inquiry"] = InquiryResourceManager(
            models.Inquiry,
            self.endpoints["api"],
            cacert=self.cacert,
            debug=self.debug,
            basic_auth=self.basic_auth,
        )
        self.managers["Pack"] = PackResourceManager(
            models.Pack,
            self.endpoints["api"],
            cacert=self.cacert,
            debug=self.debug,
            basic_auth=self.basic_auth,
        )
        self.managers["Policy"] = ResourceManager(
            models.Policy,
            self.endpoints["api"],
            cacert=self.cacert,
            debug=self.debug,
            basic_auth=self.basic_auth,
        )
        self.managers["PolicyType"] = ResourceManager(
            models.PolicyType,
            self.endpoints["api"],
            cacert=self.cacert,
            debug=self.debug,
            basic_auth=self.basic_auth,
        )
        self.managers["Rule"] = ResourceManager(
            models.Rule,
            self.endpoints["api"],
            cacert=self.cacert,
            debug=self.debug,
            basic_auth=self.basic_auth,
        )
        self.managers["Sensor"] = ResourceManager(
            models.Sensor,
            self.endpoints["api"],
            cacert=self.cacert,
            debug=self.debug,
            basic_auth=self.basic_auth,
        )
        self.managers["TriggerType"] = ResourceManager(
            models.TriggerType,
            self.endpoints["api"],
            cacert=self.cacert,
            debug=self.debug,
            basic_auth=self.basic_auth,
        )
        self.managers["Trigger"] = ResourceManager(
            models.Trigger,
            self.endpoints["api"],
            cacert=self.cacert,
            debug=self.debug,
            basic_auth=self.basic_auth,
        )
        self.managers["TriggerInstance"] = TriggerInstanceResourceManager(
            models.TriggerInstance,
            self.endpoints["api"],
            cacert=self.cacert,
            debug=self.debug,
            basic_auth=self.basic_auth,
        )
        self.managers["KeyValuePair"] = KeyValuePairResourceManager(
            models.KeyValuePair,
            self.endpoints["api"],
            cacert=self.cacert,
            debug=self.debug,
            basic_auth=self.basic_auth,
        )
        self.managers["Webhook"] = WebhookManager(
            models.Webhook,
            self.endpoints["api"],
            cacert=self.cacert,
            debug=self.debug,
            basic_auth=self.basic_auth,
        )
        self.managers["Timer"] = ResourceManager(
            models.Timer,
            self.endpoints["api"],
            cacert=self.cacert,
            debug=self.debug,
            basic_auth=self.basic_auth,
        )
        self.managers["Trace"] = ResourceManager(
            models.Trace,
            self.endpoints["api"],
            cacert=self.cacert,
            debug=self.debug,
            basic_auth=self.basic_auth,
        )
        self.managers["RuleEnforcement"] = ResourceManager(
            models.RuleEnforcement,
            self.endpoints["api"],
            cacert=self.cacert,
            debug=self.debug,
            basic_auth=self.basic_auth,
        )
        self.managers["Stream"] = StreamManager(
            self.endpoints["stream"],
            cacert=self.cacert,
            debug=self.debug,
            basic_auth=self.basic_auth,
        )
        self.managers["Workflow"] = WorkflowManager(
            self.endpoints["api"],
            cacert=self.cacert,
            debug=self.debug,
            basic_auth=self.basic_auth,
        )

        # Service Registry
        self.managers["ServiceRegistryGroups"] = ServiceRegistryGroupsManager(
            models.ServiceRegistryGroup,
            self.endpoints["api"],
            cacert=self.cacert,
            debug=self.debug,
            basic_auth=self.basic_auth,
        )

        self.managers["ServiceRegistryMembers"] = ServiceRegistryMembersManager(
            models.ServiceRegistryMember,
            self.endpoints["api"],
            cacert=self.cacert,
            debug=self.debug,
            basic_auth=self.basic_auth,
        )

        # RBAC
        self.managers["Role"] = ResourceManager(
            models.Role,
            self.endpoints["api"],
            cacert=self.cacert,
            debug=self.debug,
            basic_auth=self.basic_auth,
        )
        self.managers["UserRoleAssignment"] = ResourceManager(
            models.UserRoleAssignment,
            self.endpoints["api"],
            cacert=self.cacert,
            debug=self.debug,
            basic_auth=self.basic_auth,
        )

    @add_auth_token_to_kwargs_from_env
    def get_user_info(self, **kwargs):
        """
        Retrieve information about the current user which is authenticated against StackStorm API.

        :rtype: ``dict``
        """
        url = "/user"
        client = httpclient.HTTPClient(
            root=self.endpoints["api"],
            cacert=self.cacert,
            debug=self.debug,
            basic_auth=self.basic_auth,
        )
        response = client.get(url=url, **kwargs)

        if response.status_code != 200:
            ResourceManager.handle_error(response)

        return response.json()

    @property
    def actions(self):
        return self.managers["Action"]

    @property
    def apikeys(self):
        return self.managers["ApiKey"]

    @property
    def keys(self):
        return self.managers["KeyValuePair"]

    @property
    def executions(self):
        return self.managers["Execution"]

    # NOTE: LiveAction has been deprecated in favor of Execution. It will be left here for
    # backward compatibility reasons until v3.2.0
    @property
    def liveactions(self):
        warnings.warn(
            (
                "st2client.liveactions has been renamed to st2client.executions, please "
                "update your code"
            ),
            DeprecationWarning,
        )
        return self.executions

    @property
    def inquiries(self):
        return self.managers["Inquiry"]

    @property
    def packs(self):
        return self.managers["Pack"]

    @property
    def policies(self):
        return self.managers["Policy"]

    @property
    def policytypes(self):
        return self.managers["PolicyType"]

    @property
    def rules(self):
        return self.managers["Rule"]

    @property
    def runners(self):
        return self.managers["RunnerType"]

    @property
    def sensors(self):
        return self.managers["Sensor"]

    @property
    def tokens(self):
        return self.managers["Token"]

    @property
    def triggertypes(self):
        return self.managers["TriggerType"]

    @property
    def triggerinstances(self):
        return self.managers["TriggerInstance"]

    @property
    def trace(self):
        return self.managers["Trace"]

    @property
    def ruleenforcements(self):
        return self.managers["RuleEnforcement"]

    @property
    def webhooks(self):
        return self.managers["Webhook"]

    @property
    def workflows(self):
        return self.managers["Workflow"]
