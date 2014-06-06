from st2common.persistence import Access
from st2common.models.db.actionrunner import (liveaction_access, actionrunner_access)


class LiveAction(Access):
    IMPL = liveaction_access

    @classmethod
    def _get_impl(cls):
        return cls.IMPL


class ActionRunner(Access):
    IMPL = actionrunner_access

    @classmethod
    def _get_impl(cls):
        return cls.IMPL
