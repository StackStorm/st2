import six
import os

from st2actions.runners.pythonrunner import Action
from st2client.client import Client
from st2common.util import jinja as jinja_utils


class FormatResultAction(Action):
    def __init__(self, config):
        super(FormatResultAction, self).__init__(config)
        api_url = os.environ.get('ST2_ACTION_API_URL', None)
        token = os.environ.get('ST2_ACTION_AUTH_TOKEN', None)
        self.client = Client(api_url=api_url, token=token)
        self.jinja = jinja_utils.get_jinja_environment()
        self.jinja.tests['in'] = lambda item, list: item in list

        path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(path, 'templates/default.j2'), 'r') as f:
            self.default_template = f.read()

    def run(self, execution_id):
        execution = self._get_execution(execution_id)
        context = {
            'six': six,
            'execution': execution
        }
        template = self.default_template

        alias_id = execution['context'].get('action_alias_ref', {}).get('id', None)
        if alias_id:
            alias = self.client.managers['ActionAlias'].get_by_id(alias_id)

            context.update({
                'alias': alias
            })

            result = getattr(alias, 'result', None)
            if result:
                if not result.get('enabled', True):
                    raise Exception("Output of this template is disabled.")
                if 'format' in alias.result:
                    template = alias.result['format']

        return self.jinja.from_string(template).render(context)

    def _get_execution(self, execution_id):
        if not execution_id:
            raise ValueError('Invalid execution_id provided.')
        execution = self.client.liveactions.get_by_id(id=execution_id)
        if not execution:
            return None
        excludes = ["trigger", "trigger_type", "trigger_instance", "liveaction"]
        return execution.to_dict(exclude_attributes= excludes)
