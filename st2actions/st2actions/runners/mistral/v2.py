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

from oslo.config import cfg
from mistralclient.api import client as mistral

from st2common.constants.action import ACTIONEXEC_STATUS_RUNNING
from st2actions.runners import ActionRunner
from st2common import log as logging


LOG = logging.getLogger(__name__)


def get_runner():
    return MistralRunner(str(uuid.uuid4()))


class MistralRunner(ActionRunner):

    url = cfg.CONF.workflow.url

    def __init__(self, runner_id):
        super(MistralRunner, self).__init__(runner_id=runner_id)
        self._on_behalf_user = cfg.CONF.system_user.user

    def pre_run(self):
        pass

    def run(self, action_parameters):
        client = mistral.client(mistral_url='%s/v2' % self.url)

        # Update workbook definition.
        workbook_name = self.action.pack + '.' + self.action.name
        with open(self.entry_point, 'r') as wbkfile:
            definition = wbkfile.read()
            try:
                wbk = client.workbooks.get(workbook_name)
                if wbk.definition != definition:
                    client.workbooks.update(definition)
            except:
                client.workbooks.create(definition)

        # Setup context for the workflow execution.
        context = self.runner_parameters.get('context', dict())
        context.update(action_parameters)
        endpoint = 'http://%s:%s/v1/actionexecutions' % (cfg.CONF.api.host, cfg.CONF.api.port)
        params = {'st2_api_url': endpoint,
                  'st2_parent': self.action_execution_id}

        # Execute the workflow.
        execution = client.executions.create(self.runner_parameters.get('workflow'),
                                             workflow_input=context, **params)

        self.container_service.report_status(ACTIONEXEC_STATUS_RUNNING)
        self.container_service.report_result()
        done = (str(execution.state) == 'RUNNING')
        query_context = {'id': execution.id}
        partial_results = {'tasks': []}
        return (done, query_context, partial_results)
