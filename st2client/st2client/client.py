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

from st2client import models


LOG = logging.getLogger(__name__)


class Client(object):

    def __init__(self, *args, **kwargs):

        # Get CLI options. If not given, then try to get it from the environment.
        self.endpoints = dict()
        self.endpoints['base'] = kwargs.get('base_url')
        if not self.endpoints['base']:
            self.endpoints['base'] = os.environ.get(
                'ST2_BASE_URL', 'http://localhost')

        self.endpoints['auth'] = kwargs.get('auth_url')
        if not self.endpoints['auth']:
            base_https_url = self.endpoints['base'].replace('http://', 'https://')
            self.endpoints['auth'] = os.environ.get(
                'ST2_AUTH_URL', '%s:%s' % (base_https_url, 9100))

        api_version = kwargs.get('api_version') or os.environ.get('ST2_API_VERSION', 'v1')

        self.endpoints['api'] = kwargs.get('api_url')
        if not self.endpoints['api']:
            self.endpoints['api'] = os.environ.get(
                'ST2_API_URL', '%s:%s/%s' % (self.endpoints['base'], 9101, api_version))

        self.cacert = kwargs.get('cacert')
        if not self.cacert:
            self.cacert = os.environ.get('ST2_CACERT', None)
        if self.cacert and not os.path.isfile(self.cacert):
            raise ValueError('CA cert file "%s" does not exist.' % self.cacert)

        # Instantiate resource managers and assign appropriate API endpoint.
        self.managers = dict()
        self.managers['Token'] = models.ResourceManager(
            models.Token, self.endpoints['auth'], cacert=self.cacert)
        self.managers['RunnerType'] = models.ResourceManager(
            models.RunnerType, self.endpoints['api'], cacert=self.cacert)
        self.managers['Action'] = models.ResourceManager(
            models.Action, self.endpoints['api'], cacert=self.cacert)
        self.managers['ActionExecution'] = models.ResourceManager(
            models.ActionExecution, self.endpoints['api'], cacert=self.cacert)
        self.managers['Rule'] = models.ResourceManager(
            models.Rule, self.endpoints['api'], cacert=self.cacert)
        self.managers['Sensor'] = models.ResourceManager(
            models.Sensor, self.endpoints['api'], cacert=self.cacert)
        self.managers['Trigger'] = models.ResourceManager(
            models.Trigger, self.endpoints['api'], cacert=self.cacert)
        self.managers['KeyValuePair'] = models.ResourceManager(
            models.KeyValuePair, self.endpoints['api'], cacert=self.cacert)

    @property
    def tokens(self):
        return self.managers['Token']

    @property
    def runners(self):
        return self.managers['RunnerType']

    @property
    def actions(self):
        return self.managers['Action']

    @property
    def executions(self):
        return self.managers['ActionExecution']

    @property
    def rules(self):
        return self.managers['Rule']

    @property
    def sensors(self):
        return self.managers['Sensor']

    @property
    def triggers(self):
        return self.managers['Trigger']

    @property
    def keys(self):
        return self.managers['KeyValuePair']
