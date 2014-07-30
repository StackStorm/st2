from st2common.persistence import Access
from st2common.models.db.reactor import trigger_access, triggerinstance_access, rule_access, \
    ruleenforcement_access


class Trigger(Access):
    IMPL = trigger_access

    @classmethod
    def _get_impl(kls):
        return kls.IMPL


class TriggerInstance(Access):
    IMPL = triggerinstance_access

    @classmethod
    def _get_impl(kls):
        return kls.IMPL


class Rule(Access):
    IMPL = rule_access

    @classmethod
    def _get_impl(kls):
        return kls.IMPL


class RuleEnforcement(Access):
    IMPL = ruleenforcement_access

    @classmethod
    def _get_impl(kls):
        return kls.IMPL
