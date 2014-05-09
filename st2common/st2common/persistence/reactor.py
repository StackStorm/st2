from st2common.persistence import Access
from st2common.models.db.reactor import triggersource_access, \
    trigger_access, triggerinstance_access, rule_access, \
    ruleenforcement_access


class TriggerSource(Access):
    IMPL = triggersource_access

    @classmethod
    def _get_impl(cls):
        return cls.IMPL


class Trigger(Access):
    IMPL = trigger_access

    @classmethod
    def _get_impl(cls):
        return cls.IMPL


class TriggerInstance(Access):
    IMPL = triggerinstance_access

    @classmethod
    def _get_impl(cls):
        return cls.IMPL


class Rule(Access):
    IMPL = rule_access

    @classmethod
    def _get_impl(cls):
        return cls.IMPL


class RuleEnforcement(Access):
    IMPL = ruleenforcement_access

    @classmethod
    def _get_impl(cls):
        return cls.IMPL
