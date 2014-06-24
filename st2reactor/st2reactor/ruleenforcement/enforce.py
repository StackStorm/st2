import json
from st2common import log as logging
import requests
from oslo.config import cfg
from st2reactor.ruleenforcement.datatransform import get_transformer
from st2reactor.ruleenforcement.filter import get_filter
from st2common.models.db.reactor import RuleEnforcementDB
from st2common.persistence.reactor import RuleEnforcement, Rule
from st2common.persistence.action import ActionExecution


LOG = logging.getLogger('st2reactor.ruleenforcement.enforce')
HTTP_AE_POST_HEADER = {'content-type': 'application/json'}


def handle_trigger_instances(trigger_instances):
    enforcers = [RuleEnforcer(trigger_instance)
                 for trigger_instance in trigger_instances]
    for enforcer in enforcers:
        enforcer.enforce()


class RuleEnforcer(object):
    def __init__(self, trigger_instance):
        self.trigger_instance = trigger_instance
        self.data_transformer = get_transformer(trigger_instance.payload)
        self.filter = get_filter(trigger_instance)

    def enforce(self):
        rules = RuleEnforcer.__get_rules(self.filter.apply_filter,
                                         self.trigger_instance)
        LOG.info('%d rule(s) found to enforce for %s.', len(rules),
                 self.trigger_instance.trigger.name)
        for rule in rules:
            rule_enforcement = RuleEnforcementDB()
            rule_enforcement.trigger_instance = self.trigger_instance
            rule_enforcement.rule = rule
            data = self.data_transformer(rule.action.data_mapping, rule.rule_data)
            LOG.info('Invoking action %s for trigger_instance %s with data %s.',
                     RuleEnforcer.__get_action_name(rule.action), self.trigger_instance.id,
                     json.dumps(data))
            action_execution = RuleEnforcer.__invoke_action(rule.action.action, data)
            rule_enforcement.action_execution = action_execution
            rule_enforcement = RuleEnforcement.add_or_update(rule_enforcement)
            LOG.audit('[re=%s] ActionExecution %s for TriggerInstance %s due to Rule %s.',
                     rule_enforcement.id, action_execution.id, rule.id, self.trigger_instance.id)

    @staticmethod
    def __get_rules(filter_func, trigger_instance):
        return filter(filter_func,
                      Rule.query(trigger_type=trigger_instance.trigger, enabled=True))

    @staticmethod
    def __get_action_name(action_exec_spec):
        if action_exec_spec is None or action_exec_spec.action is None:
            return ''
        return action_exec_spec.action.name

    @staticmethod
    def __invoke_action(action, action_args):
        payload = json.dumps({'action': {'name': action.name},
                              'runner_parameters': {},
                              'action_parameters': action_args})
        r = requests.post(cfg.CONF.reactor.actionexecution_base_url,
                          data=payload,
                          headers=HTTP_AE_POST_HEADER)
        if r.status_code != 201:
            return None
        action_execution_id = r.json()['id']
        return ActionExecution.get_by_id(action_execution_id)
