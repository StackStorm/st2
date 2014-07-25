from st2common.persistence import Access
from st2common.models.db.action import (actiontype_access, action_access, actionexec_access)


class ActionType(Access):
    IMPL = actiontype_access

    @classmethod
    def _get_impl(kls):
        return kls.IMPL

class Action(Access):
    IMPL = action_access

    @classmethod
    def _get_impl(kls):
        return kls.IMPL


class ActionExecution(Access):
    IMPL = actionexec_access

    @classmethod
    def _get_impl(kls):
        return kls.IMPL
