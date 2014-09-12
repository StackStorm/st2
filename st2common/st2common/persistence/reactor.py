from oslo.config import cfg
from st2common import transport
from st2common.persistence import Access
from st2common.models.db.reactor import triggertype_access, trigger_access, triggerinstance_access,\
    rule_access, ruleenforcement_access


class TriggerType(Access):
    impl = triggertype_access

    @classmethod
    def _get_impl(kls):
        return kls.impl


class Trigger(Access):
    impl = trigger_access
    publisher = None

    @classmethod
    def _get_impl(kls):
        return kls.impl

    @classmethod
    def _get_publisher(kls):
        if not kls.publisher:
            kls.publisher = transport.reactor.TriggerPublisher(cfg.CONF.messaging.url)
        return kls.publisher


class TriggerInstance(Access):
    impl = triggerinstance_access

    @classmethod
    def _get_impl(kls):
        return kls.impl


class Rule(Access):
    impl = rule_access

    @classmethod
    def _get_impl(kls):
        return kls.impl


class RuleEnforcement(Access):
    impl = ruleenforcement_access

    @classmethod
    def _get_impl(kls):
        return kls.impl
