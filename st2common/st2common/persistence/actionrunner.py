from st2common.persistence import Access
from st2common.models.db.actionrunner import actionrunner_access


class ActionRunner(Access):
    IMPL = actionrunner_access

    @classmethod
    def _get_impl(kls):
        return kls.IMPL
