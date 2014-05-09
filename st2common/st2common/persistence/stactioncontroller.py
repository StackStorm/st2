from st2common.persistence import Access
from st2common.models.db.stactioncontroller import staction_access


class Staction(Access):
    IMPL = staction_access

    @classmethod
    def _get_impl(cls):
        return cls.IMPL
