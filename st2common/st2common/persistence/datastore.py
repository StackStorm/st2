from st2common import persistence
from st2common.models.db import datastore


class KeyValuePair(persistence.Access):
    IMPL = datastore.keyvaluepair_access

    @classmethod
    def _get_impl(cls):
        return cls.IMPL
