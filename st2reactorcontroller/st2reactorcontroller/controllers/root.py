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

    @expose('error.html')
    def error(self, status):
        try:
            status = int(status)
        except ValueError:  # pragma: no cover
            status = 500
        message = getattr(status_map.get(status), 'explanation', '')
        return dict(status=status, message=message)
