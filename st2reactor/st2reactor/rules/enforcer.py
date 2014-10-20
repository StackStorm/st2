import json

from st2common import log as logging
from st2common.util import reference
from st2reactor.rules.datatransform import get_transformer
from st2common.models.db.reactor import RuleEnforcementDB
from st2common.persistence.reactor import RuleEnforcement
from st2common.services import action as action_service
from st2common.models.db.action import ActionExecutionDB
from st2common.models.api.constants import ACTIONEXEC_STATUS_SCHEDULED
from st2common.models.api.access import get_system_username


LOG = logging.getLogger('st2reactor.ruleenforcement.enforce')


class RuleEnforcer(object):
    def __init__(self, trigger_instance, rule):
        self.trigger_instance = trigger_instance
        self.rule = rule
        self.data_transformer = get_transformer(trigger_instance.payload)

    def enforce(self):
        rule_enforcement = RuleEnforcementDB()
        rule_enforcement.trigger_instance = reference.get_ref_from_model(self.trigger_instance)
        rule_enforcement.rule = reference.get_ref_from_model(self.rule)
        data = self.data_transformer(self.rule.action.parameters)
        LOG.info('Invoking action %s for trigger_instance %s with data %s.',
                 self.rule.action.name, self.trigger_instance.id,
                 json.dumps(data))
        context = {'trigger_instance': reference.get_ref_from_model(self.trigger_instance),
                   'rule': reference.get_ref_from_model(self.rule),
                   'user': get_system_username()}
        action_execution = RuleEnforcer._invoke_action(self.rule.action.name, data, context)
        if action_execution is not None:
            rule_enforcement.action_execution = action_execution
            LOG.audit('Rule enforced. ActionExecution %s, TriggerInstance %s and Rule %s.',
                      action_execution.get('id', None), self.trigger_instance, self.rule)
        else:
            rule_enforcement.action_execution = {}
            LOG.audit('Rule enforcement failed. ActionExecution for Action %s failed. '
                      'TriggerInstance: %s and Rule: %s',
                      self.rule.action.name, self.trigger_instance, self.rule)
        rule_enforcement = RuleEnforcement.add_or_update(rule_enforcement)

    @staticmethod
    def _invoke_action(action_name, action_args, context=None):
        action = {'name': action_name}
        execution = ActionExecutionDB(action=action, context=context, parameters=action_args)
        execution = action_service.schedule(execution)
        return ({'id': str(execution.id)}
                if execution.status == ACTIONEXEC_STATUS_SCHEDULED else None)
