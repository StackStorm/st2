import uuid

from oslo.config import cfg
from mistralclient.api import client as mistral

from st2common.models.api.constants import ACTIONEXEC_STATUS_RUNNING
from st2actions.runners import ActionRunner
from st2common import log as logging


LOG = logging.getLogger(__name__)


def get_runner():
    return MistralRunner(str(uuid.uuid4()))


class MistralRunner(ActionRunner):

    url = cfg.CONF.workflow.url

    def __init__(self, id):
        super(MistralRunner, self).__init__()
        self._on_behalf_user = cfg.CONF.system_user.user

    def pre_run(self):
        pass

    def run(self, action_parameters):
        client = mistral.client(mistral_url='%s/v2' % self.url)

        # Update workbook definition.
        with open(self.entry_point, 'r') as wbkfile:
            definition = wbkfile.read()
            try:
                wbk = client.workbooks.get(self.action.name)
                if wbk.definition != definition:
                    client.workbooks.update(definition)
            except:
                client.workbooks.create(definition)

        # Setup context for the workflow execution.
        context = self.runner_parameters.get('context', dict())
        context.update(action_parameters)
        endpoint = 'http://%s:%s/actionexecutions' % (cfg.CONF.api.host, cfg.CONF.api.port)
        params = {'st2_api_url': endpoint,
                  'st2_parent': self.action_execution_id}

        # Execute the workflow.
        execution = client.executions.create(self.runner_parameters.get('workflow'),
                                             workflow_input=context, **params)

        # Return status and output.
        output = {
            'id': str(execution.id),
            'state': str(execution.state)
        }

        self.container_service.report_status(ACTIONEXEC_STATUS_RUNNING)
        self.container_service.report_result(output)

        return (str(execution.state) == 'RUNNING')
