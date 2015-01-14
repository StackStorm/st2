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
import yaml

from oslo.config import cfg
from mistralclient.api import client as mistral

from st2common.constants.action import ACTIONEXEC_STATUS_RUNNING
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

    def pre_run(self):
        pass

    def _find_default_workflow(self, definition):
        def_dict = yaml.safe_load(definition)
        num_workflows = len(def_dict['workflows'].keys())

        if num_workflows > 1:
            fully_qualified_wf_name = self.runner_parameters.get('workflow')
            if not fully_qualified_wf_name:
                raise ValueError('Default workflow to run is not provided for the workbook.')

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
        client = mistral.client(mistral_url='%s/v2' % self.url)

        # Update workbook definition.
        workbook_name = self.action.pack + '.' + self.action.name
        with open(self.entry_point, 'r') as wbkfile:
            definition = wbkfile.read()
            transformed_definition = utils.transform_definition(definition)
            try:
                wbk = client.workbooks.get(workbook_name)
                if wbk.definition != transformed_definition:
                    client.workbooks.update(transformed_definition)
            except:
                client.workbooks.create(transformed_definition)

        # Setup context for the workflow execution.
        context = self.runner_parameters.get('context', dict())
        context.update(action_parameters)
        endpoint = 'http://%s:%s/v1/actionexecutions' % (cfg.CONF.api.host, cfg.CONF.api.port)
        params = {'st2_api_url': endpoint,
                  'st2_parent': self.action_execution_id}

        # Determine the default workflow in the workbook to run.
        default_workflow = self._find_default_workflow(transformed_definition)

        # Execute the workflow.
        execution = client.executions.create(default_workflow, workflow_input=context, **params)

        status = ACTIONEXEC_STATUS_RUNNING
        query_context = {'mistral_execution_id': str(execution.id)}
        LOG.info('Mistral query_context is %s' % query_context)
        partial_results = {'tasks': []}

        return (status, partial_results, query_context)
