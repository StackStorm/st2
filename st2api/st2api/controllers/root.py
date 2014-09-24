from pecan import expose

from st2api.controllers.actions import ActionsController
from st2api.controllers.actionexecutions import ActionExecutionsController
from st2api.controllers.runnertypes import RunnerTypesController
from st2api.controllers.triggers import TriggerTypeController, TriggerController, \
    TriggerInstanceController
from st2api.controllers.rules import RuleController
from st2api.controllers.datastore import KeyValuePairController


class RootController(object):
    actions = ActionsController()
    actionexecutions = ActionExecutionsController()
    runnertypes = RunnerTypesController()
    triggertypes = TriggerTypeController()
    triggers = TriggerController()
    triggerinstances = TriggerInstanceController()
    rules = RuleController()
    keys = KeyValuePairController()

    @expose(generic=True, template='index.html')
    def index(self):
        return dict()
