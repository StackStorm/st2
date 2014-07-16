import json
from st2common import log as logging
import requests
from oslo.config import cfg
from st2reactor.rules.datatransform import get_transformer
from st2common.models.db.reactor import RuleEnforcementDB
from st2common.persistence.reactor import RuleEnforcement
from st2common.util import reference


LOG = logging.getLogger('st2reactor.ruleenforcement.enforce')
HTTP_AE_POST_HEADER = {'content-type': 'application/json'}


class RuleEnforcer(object):
    def __init__(self, trigger_instance, rule):
        self.trigger_instance = trigger_instance
        self.rule = rule
        self.data_transformer = get_transformer(trigger_instance.payload)

    def enforce(self):
        rule_enforcement = RuleEnforcementDB()
        rule_enforcement.trigger_instance = reference.get_ref_from_model(self.trigger_instance)
        rule_enforcement.rule = reference.get_ref_from_model(self.rule)
        data = self.data_transformer(self.rule.action.data_mapping, self.rule.rule_data)
        LOG.info('Invoking action %s for trigger_instance %s with data %s.',
                 RuleEnforcer.__get_action_name(self.rule.action), self.trigger_instance.id,
                 json.dumps(data))
        action_execution = RuleEnforcer.__invoke_action(self.rule.action.action, data)
        rule_enforcement.action_execution = action_execution
        rule_enforcement = RuleEnforcement.add_or_update(rule_enforcement)
        LOG.audit('[re=%s] ActionExecution %s for TriggerInstance %s due to Rule %s.',
                 rule_enforcement.id, action_execution.get('id', None), self.rule.id,
                 self.trigger_instance.id)

    @staticmethod
    def __get_action_name(action_exec_spec):
        if action_exec_spec is None or action_exec_spec.action is None:
            return ''
        return action_exec_spec.action['name']

    @staticmethod
    def __invoke_action(action, action_args):
        payload = json.dumps({'action': action,
                              'runner_parameters': {},
                              'action_parameters': action_args})
        r = requests.post(cfg.CONF.reactor.actionexecution_base_url,
                          data=payload,
                          headers=HTTP_AE_POST_HEADER)
        if r.status_code != 201:
            return None
        action_execution_id = r.json()['id']
        return {'id': action_execution_id}
