import abc
import six

from st2common.models.db.reactor import triggersource_access, \
    trigger_access, triggerinstance_access, rule_access, \
    ruleenforcement_access

@six.add_metaclass(abc.ABCMeta)
class Access(object):

    @classmethod
    @abc.abstractmethod
    def _get_impl(cls):
        """ """

    @classmethod
    def get_by_name(cls, value):
        cls._get_impl().get_by_name(value)

    @classmethod
    def get_by_id(cls, value):
        cls._get_impl().get_by_id(value)

    @classmethod
    def get_all(cls):
        cls._get_impl().get_all()

    @classmethod
    def add_or_update(cls, model_object):
        cls.add_or_update(model_object)


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
