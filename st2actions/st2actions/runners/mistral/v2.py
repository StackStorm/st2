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

import uuid

from mistralclient.api import client as mistral
from oslo.config import cfg
import six
import yaml

from st2common.constants.action import LIVEACTION_STATUS_RUNNING
from st2actions.runners import AsyncActionRunner
from st2actions.runners.mistral import utils
from st2common import log as logging


LOG = logging.getLogger(__name__)


def get_runner():
    return MistralRunner(str(uuid.uuid4()))


class MistralRunner(AsyncActionRunner):

    url = cfg.CONF.workflow.url

    def __init__(self, runner_id):
        super(MistralRunner, self).__init__(runner_id=runner_id)
        self._on_behalf_user = cfg.CONF.system_user.user
        self._client = mistral.client(mistral_url='%s/v2' % self.url)

    def pre_run(self):
        pass

    @staticmethod
    def _check_name(action_ref, is_workbook, def_dict):
        # If workbook, change the value of the "name" key.
        if is_workbook:
            if def_dict.get('name') != action_ref:
                raise Exception('Name of the workbook must be the same as the '
                                'fully qualified action name "%s".' % action_ref)
        # If workflow, change the key name of the workflow.
        else:
            workflow_name = [k for k, v in six.iteritems(def_dict) if k != 'version'][0]
            if workflow_name != action_ref:
                raise Exception('Name of the workflow must be the same as the '
                                'fully qualified action name "%s".' % action_ref)

    def _save_workbook(self, name, def_yaml):
        # If the workbook is not found, the mistral client throws a generic API exception.
        try:
            # Update existing workbook.
            wb = self._client.workbooks.get(name)
        except:
            # Delete if definition was previously a workflow.
            # If not found, an API exception is thrown.
            try:
                self._client.workflows.delete(name)
            except:
                pass

            # Create the new workbook.
            wb = self._client.workbooks.create(def_yaml)

        # Update the workbook definition.
        if wb.definition != def_yaml:
            self._client.workbooks.update(def_yaml)

    def _save_workflow(self, name, def_yaml):
        # If the workflow is not found, the mistral client throws a generic API exception.
        try:
            # Update existing workbook.
            wf = self._client.workflows.get(name)
        except:
            # Delete if definition was previously a workbook.
            # If not found, an API exception is thrown.
            try:
                self._client.workbooks.delete(name)
            except:
                pass

            # Create the new workflow.
            wf = self._client.workflows.create(def_yaml)[0]

        # Update the workflow definition.
        if wf.definition != def_yaml:
            self._client.workflows.update(def_yaml)

    def _find_default_workflow(self, def_dict):
        num_workflows = len(def_dict['workflows'].keys())

        if num_workflows > 1:
            fully_qualified_wf_name = self.runner_parameters.get('workflow')
            if not fully_qualified_wf_name:
                raise ValueError('Workbook definition is detected. '
                                 'Default workflow cannot be determined.')

            wf_name = fully_qualified_wf_name[fully_qualified_wf_name.rindex('.') + 1:]
            if wf_name not in def_dict['workflows']:
                raise ValueError('Unable to find the workflow "%s" in the workbook.'
                                 % fully_qualified_wf_name)

            return fully_qualified_wf_name
        elif num_workflows == 1:
            return '%s.%s' % (def_dict['name'], def_dict['workflows'].keys()[0])
        else:
            raise Exception('There are no workflows in the workbook.')

    def run(self, action_parameters):
        # Setup inputs for the workflow execution.
        inputs = self.runner_parameters.get('context', dict())
        inputs.update(action_parameters)
        endpoint = 'http://%s:%s/v1/actionexecutions' % (cfg.CONF.api.host, cfg.CONF.api.port)
        options = {
            'st2_api_url': endpoint,
            'st2_parent': self.liveaction_id
        }

        # Get workbook/workflow definition from file.
        with open(self.entry_point, 'r') as def_file:
            def_yaml = def_file.read()

        def_dict = yaml.safe_load(def_yaml)
        is_workbook = ('workflows' in def_dict)

        if not is_workbook:
            # Non-workbook definition containing multiple workflows is not supported.
            if len([k for k, v in six.iteritems(def_dict) if k != 'version']) != 1:
                raise Exception('Workflow (not workbook) definition is detected. '
                                'Multiple workflows is not supported.')

        action_ref = '%s.%s' % (self.action.pack, self.action.name)
        self._check_name(action_ref, is_workbook, def_dict)
        def_dict_xformed = utils.transform_definition(def_dict)
        def_yaml_xformed = yaml.safe_dump(def_dict_xformed, default_flow_style=False)

        # Save workbook/workflow definition.
        if is_workbook:
            self._save_workbook(action_ref, def_yaml_xformed)
            default_workflow = self._find_default_workflow(def_dict_xformed)
            execution = self._client.executions.create(default_workflow,
                                                       workflow_input=inputs,
                                                       **options)
        else:
            self._save_workflow(action_ref, def_yaml_xformed)
            execution = self._client.executions.create(action_ref,
                                                       workflow_input=inputs,
                                                       **options)

        status = LIVEACTION_STATUS_RUNNING
        query_context = {'mistral_execution_id': str(execution.id)}
        LOG.info('Mistral query_context is %s' % query_context)
        partial_results = {'tasks': []}

        return (status, partial_results, query_context)
