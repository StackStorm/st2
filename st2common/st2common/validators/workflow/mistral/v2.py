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

import re

import six
import yaml
from mistralclient.api import client as mistral
from oslo_config import cfg

from st2common.exceptions.workflow import WorkflowDefinitionException
from st2common import log as logging
from st2common.util.workflow import mistral as utils
from st2common.util.url import get_url_without_trailing_slash
from st2common.validators.workflow.base import WorkflowValidator


LOG = logging.getLogger(__name__)


def get_validator():
    return MistralWorkflowValidator()


class MistralWorkflowValidator(WorkflowValidator):

    url = get_url_without_trailing_slash(cfg.CONF.mistral.v2_base_url)

    def __init__(self):
        super(MistralWorkflowValidator, self).__init__()
        self._client = mistral.client(
            mistral_url=self.url,
            username=cfg.CONF.mistral.keystone_username,
            api_key=cfg.CONF.mistral.keystone_password,
            project_name=cfg.CONF.mistral.keystone_project_name,
            auth_url=cfg.CONF.mistral.keystone_auth_url)

    @staticmethod
    def parse(message):
        result = {
            'type': None,
            'path': None,
            'message': message
        }

        # Check message for schema specific error.
        m1 = re.search('^Invalid DSL: (.+)\n', message)

        if m1:
            result['type'] = 'schema'
            result['message'] = m1.group(1)

            path = re.search('On instance(.+):', message)

            if path:
                result['path'] = path.group(1).strip("[']").replace("']['", ".")

        # Check message for YAQL specific error.
        m2 = re.search('^Parse error: (.+)$', message)

        if m2:
            result['type'] = 'yaql'
            result['message'] = m2.group(1)

        # Check message for action parameters specific error.
        if any([candidate in message
                for candidate in ['Missing required parameters',
                                  'Unexpected parameters',
                                  'st2.callback is deprecated']]):
            result['type'] = 'action'

        return result

    def validate(self, definition):
        def_dict = yaml.safe_load(definition)
        is_workbook = ('workflows' in def_dict)

        if not is_workbook:
            # Non-workbook definition containing multiple workflows is not supported.
            if len([k for k, _ in six.iteritems(def_dict) if k != 'version']) != 1:
                return [self.parse('Multiple workflows is not supported workflow '
                                   'only (not a workbook) definition.')]

        # Select validation function.
        func = self._client.workbooks.validate if is_workbook else self._client.workflows.validate

        # Validate before custom DSL transformation.
        result = func(definition)

        if not result.get('valid', None):
            return [self.parse(result.get('error', 'Unknown exception.'))]

        try:
            # Run custom DSL transformer to check action parameters.
            utils.transform_definition(def_dict)
        except WorkflowDefinitionException as e:
            return [self.parse(e.message)]

        return []
