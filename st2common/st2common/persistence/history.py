from st2common.persistence import Access
from st2common.models.db import MongoDBAccess
from st2common.models.db.history import ActionExecutionHistoryDB


class ActionExecutionHistory(Access):
    impl = MongoDBAccess(ActionExecutionHistoryDB)

    @classmethod
    def _get_impl(kls):
        return kls.impl
