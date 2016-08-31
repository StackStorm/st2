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
import logging

import six

from st2client import models
from st2client.models.core import ResourceManager
from st2client.models.core import ActionAliasResourceManager
from st2client.models.core import LiveActionResourceManager
from st2client.models.core import TriggerInstanceResourceManager
from st2client.models.core import PackResourceManager


LOG = logging.getLogger(__name__)

# Default values for the options not explicitly specified by the user
DEFAULT_API_PORT = 9101
DEFAULT_AUTH_PORT = 9100

DEFAULT_BASE_URL = 'http://127.0.0.1'
DEFAULT_API_VERSION = 'v1'


class Client(object):
    def __init__(self, base_url=None, auth_url=None, api_url=None, api_version=None, cacert=None,
                 debug=False, token=None, api_key=None):
        # Get CLI options. If not given, then try to get it from the environment.
        self.endpoints = dict()

        # Populate the endpoints
        if base_url:
            self.endpoints['base'] = base_url
        else:
            self.endpoints['base'] = os.environ.get('ST2_BASE_URL', DEFAULT_BASE_URL)

        api_version = api_version or os.environ.get('ST2_API_VERSION', DEFAULT_API_VERSION)

        if api_url:
            self.endpoints['api'] = api_url
        else:
            self.endpoints['api'] = os.environ.get(
                'ST2_API_URL', '%s:%s/%s' % (self.endpoints['base'], DEFAULT_API_PORT, api_version))

        if auth_url:
            self.endpoints['auth'] = auth_url
        else:
            self.endpoints['auth'] = os.environ.get(
                'ST2_AUTH_URL', '%s:%s' % (self.endpoints['base'], DEFAULT_AUTH_PORT))

        if cacert is not None:
            self.cacert = cacert
        else:
            self.cacert = os.environ.get('ST2_CACERT', None)

        # Note: boolean is also a valid value for "cacert"
        is_cacert_string = isinstance(self.cacert, six.string_types)
        if (self.cacert and is_cacert_string and not os.path.isfile(self.cacert)):
            raise ValueError('CA cert file "%s" does not exist.' % (self.cacert))

        self.debug = debug

        # Note: This is a nasty hack for now, but we need to get rid of the decrator abuse
        if token:
            os.environ['ST2_AUTH_TOKEN'] = token

        self.token = token

        if api_key:
            os.environ['ST2_API_KEY'] = api_key

        self.api_key = api_key

        # Instantiate resource managers and assign appropriate API endpoint.
        self.managers = dict()
        self.managers['Token'] = ResourceManager(
            models.Token, self.endpoints['auth'], cacert=self.cacert, debug=self.debug)
        self.managers['RunnerType'] = ResourceManager(
            models.RunnerType, self.endpoints['api'], cacert=self.cacert, debug=self.debug)
        self.managers['Action'] = ResourceManager(
            models.Action, self.endpoints['api'], cacert=self.cacert, debug=self.debug)
        self.managers['ActionAlias'] = ActionAliasResourceManager(
            models.ActionAlias, self.endpoints['api'], cacert=self.cacert, debug=self.debug)
        self.managers['ApiKey'] = ResourceManager(
            models.ApiKey, self.endpoints['api'], cacert=self.cacert, debug=self.debug)
        self.managers['LiveAction'] = LiveActionResourceManager(
            models.LiveAction, self.endpoints['api'], cacert=self.cacert, debug=self.debug)
        self.managers['Pack'] = PackResourceManager(
            models.Pack, self.endpoints['api'], cacert=self.cacert, debug=self.debug)
        self.managers['Policy'] = ResourceManager(
            models.Policy, self.endpoints['api'], cacert=self.cacert, debug=self.debug)
        self.managers['PolicyType'] = ResourceManager(
            models.PolicyType, self.endpoints['api'], cacert=self.cacert, debug=self.debug)
        self.managers['Rule'] = ResourceManager(
            models.Rule, self.endpoints['api'], cacert=self.cacert, debug=self.debug)
        self.managers['Sensor'] = ResourceManager(
            models.Sensor, self.endpoints['api'], cacert=self.cacert, debug=self.debug)
        self.managers['TriggerType'] = ResourceManager(
            models.TriggerType, self.endpoints['api'], cacert=self.cacert, debug=self.debug)
        self.managers['Trigger'] = ResourceManager(
            models.Trigger, self.endpoints['api'], cacert=self.cacert, debug=self.debug)
        self.managers['TriggerInstance'] = TriggerInstanceResourceManager(
            models.TriggerInstance, self.endpoints['api'], cacert=self.cacert, debug=self.debug)
        self.managers['KeyValuePair'] = ResourceManager(
            models.KeyValuePair, self.endpoints['api'], cacert=self.cacert, debug=self.debug)
        self.managers['Webhook'] = ResourceManager(
            models.Webhook, self.endpoints['api'], cacert=self.cacert, debug=self.debug)
        self.managers['Trace'] = ResourceManager(
            models.Trace, self.endpoints['api'], cacert=self.cacert, debug=self.debug)
        self.managers['RuleEnforcement'] = ResourceManager(
            models.RuleEnforcement, self.endpoints['api'], cacert=self.cacert, debug=self.debug)

    @property
    def actions(self):
        return self.managers['Action']

    @property
    def apikeys(self):
        return self.managers['ApiKey']

    @property
    def keys(self):
        return self.managers['KeyValuePair']

    @property
    def liveactions(self):
        return self.managers['LiveAction']

    @property
    def packs(self):
        return self.managers['Pack']

    @property
    def policies(self):
        return self.managers['Policy']

    @property
    def policytypes(self):
        return self.managers['PolicyType']

    @property
    def rules(self):
        return self.managers['Rule']

    @property
    def runners(self):
        return self.managers['RunnerType']

    @property
    def sensors(self):
        return self.managers['Sensor']

    @property
    def tokens(self):
        return self.managers['Token']

    @property
    def triggertypes(self):
        return self.managers['TriggerType']

    @property
    def triggerinstances(self):
        return self.managers['TriggerInstance']

    @property
    def trace(self):
        return self.managers['Trace']

    @property
    def ruleenforcements(self):
        return self.managers['RuleEnforcement']
