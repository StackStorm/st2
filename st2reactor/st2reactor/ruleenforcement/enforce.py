from st2reactor.ruleenforcement.datatransform import get_transformer
from st2common.models.db.reactor import RuleEnforcementDB
from st2common.persistence.reactor import RuleEnforcement, Rule


def handle_trigger_instances(trigger_instances):
    enforcers = [RuleEnforcer(trigger_instance)
                 for trigger_instance in trigger_instances]
    for enforcer in enforcers:
        enforcer.enforce()


class RuleEnforcer(object):
    def __init__(self, trigger_instance):
        self.trigger_instance = trigger_instance
        self.data_transformer = get_transformer(trigger_instance.payload)

    def enforce(self):
        rules = RuleEnforcer.__get_rules(self.trigger_instance)
        for rule in rules:
            rule_enforcement = RuleEnforcementDB()
            rule_enforcement.trigger_instance = self.trigger_instance
            rule_enforcement.rule = rule
            data = self.data_transformer(rule.data_mapping)
            staction = self.__invoke_staction(rule.staction, data)
            rule_enforcement.staction_execution = staction
            RuleEnforcement.add_or_update(rule_enforcement)

    @staticmethod
    def __get_rules(trigger_instance):
        return Rule.query(trigger=trigger_instance.trigger)

    @staticmethod
    def __invoke_staction(staction, staction_args):
        return staction
