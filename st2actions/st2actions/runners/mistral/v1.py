import uuid

from oslo.config import cfg
from mistralclient.api import client as mistral

from st2common.models.api.action import ACTIONEXEC_STATUS_RUNNING
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
        client = mistral.client(mistral_url=self.url)

        # Update workbook definition.
        workbook = next((w for w in client.workbooks.list() if w.name == self.action.name), None)
        if not workbook:
            client.workbooks.create(self.action.name, description=self.action.description)
        workbook_file = self.entry_point
        with open(workbook_file, 'r') as workbook_spec:
            definition = workbook_spec.read()
            try:
                old_definition = client.workbooks.get_definition(self.action.name)
            except:
                old_definition = None
            if definition != old_definition:
                client.workbooks.upload_definition(self.action.name, definition)

        # Setup context for the workflow execution.
        context = self.runner_parameters.get('context', dict())
        context['st2_parent_exec_id'] = self.action_execution_id
        context['st2_action_exec_url'] = ('http://%s:%s/actionexecutions' % (
                                          cfg.CONF.api.host, cfg.CONF.api.port))
        context.update(action_parameters)

        # Execute the workflow.
        execution = client.executions.create(self.runner_parameters.get('workbook'),
                                             self.runner_parameters.get('task'),
                                             context=context)

        # Return status and output.
        output = {
            'id': str(execution.id),
            'state': str(execution.state)
        }

        self.container_service.report_status(ACTIONEXEC_STATUS_RUNNING)
        self.container_service.report_result(output)

        return (str(execution.state) == 'RUNNING')
