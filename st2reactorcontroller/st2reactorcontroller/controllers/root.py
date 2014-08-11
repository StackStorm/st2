from pecan import expose
from webob.exc import status_map

import st2reactorcontroller.controllers.triggers
import st2reactorcontroller.controllers.rules


class RootController(object):

    triggers = st2reactorcontroller.controllers.triggers.TriggerController()
    triggerinstances = \
        st2reactorcontroller.controllers.triggers.TriggerInstanceController()
    rules = st2reactorcontroller.controllers.rules.RuleController()
    ruleenforcements = \
        st2reactorcontroller.controllers.rules.RuleEnforcementController()

    @expose(generic=True, template='index.html')
    def index(self):
        return dict()
