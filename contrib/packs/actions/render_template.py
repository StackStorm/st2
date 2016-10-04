import six
import os

from st2actions.runners.pythonrunner import Action
from st2client.client import Client
from st2common.util import jinja as jinja_utils


class RenderTemplateAction(Action):
    def __init__(self, config=None, action_service=None):
        super(RenderTemplateAction, self).__init__(config=config, action_service=action_service)
        self.jinja = jinja_utils.get_jinja_environment(allow_undefined=True)
        self.jinja.tests['in'] = lambda item, list: item in list

    def run(self, template_path, context):
        path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(path, template_path), 'r') as f:
            template = f.read()

        result = self.jinja.from_string(template).render(context)

        return result
