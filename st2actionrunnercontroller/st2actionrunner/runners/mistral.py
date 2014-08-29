import uuid

from oslo.config import cfg
from mistralclient.api import client as mistral

from st2common.models.api import action
from st2actionrunner.runners import ActionRunner
from st2common import log as logging


LOG = logging.getLogger(__name__)


def get_runner_class():
    return MistralRunner


def get_runner():
    return MistralRunner(str(uuid.uuid4()))


class MistralRunner(ActionRunner):

    url = 'http://%s:%s/v1' % (cfg.CONF.workflow.host, cfg.CONF.workflow.port)

    def __init__(self, id):
        super(MistralRunner, self).__init__()
        self._on_behalf_user = cfg.CONF.ssh_runner.user

    @classmethod
    def on_action_update(cls, action):
        client = mistral.Client(mistral_url=cls.url)

        workbook = next((wb for wb in client.workbooks.list() if wb.name == action.name), None)
        if not workbook:
            client.workbooks.create(action.name, description=action.description)

        workbook_file = cfg.CONF.actions.modules_path + '/' + action.entry_point
        with open(workbook_file, 'r') as workbook_spec:
            definition = workbook_spec.read()
            try:
                old_definition = client.workbooks.get_definition(action.name)
            except:
                old_definition = None
            if definition != old_definition:
                client.workbooks.upload_definition(action.name, definition)

    def pre_run(self):
        pass

    def run(self, action_parameters):
        client = mistral.Client(mistral_url=self.url)

        context = self.runner_parameters.get('context', dict())
        context['st2_parent_exec_id'] = self.action_execution_id
        context['st2_action_exec_url'] = ('http://%s:%s/actionexecutions' % (
                                          cfg.CONF.core_api.host, cfg.CONF.core_api.port))
        context.update(action_parameters)

        execution = client.executions.create(self.runner_parameters.get('workbook'),
                                             self.runner_parameters.get('task'),
                                             context=context)

        output = {
            'id': str(execution.id),
            'state': str(execution.state)
        }

        self.container_service.report_status(action.ACTIONEXEC_STATUS_RUNNING)
        self.container_service.report_result(output)

        return (str(execution.state) == 'RUNNING')

    def post_run(self):
        super(MistralRunner, self).post_run()
