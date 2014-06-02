from st2common.persistence import Access
from st2common.models.db.action import (action_access, actionexec_access)


class Action(Access):
    IMPL = action_access

    @classmethod
    def _get_impl(cls):
        return cls.IMPL


class ActionExecution(Access):
    IMPL = actionexec_access

    @classmethod
    def _get_impl(cls):
        return cls.IMPL
