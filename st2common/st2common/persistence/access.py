from st2common.persistence import Access
from st2common.models.db import MongoDBAccess
from st2common.models.db.access import UserDB, TokenDB


class User(Access):
    impl = MongoDBAccess(UserDB)

    @classmethod
    def _get_impl(kls):
        return kls.impl


class Token(Access):
    impl = MongoDBAccess(TokenDB)

    @classmethod
    def _get_impl(kls):
        return kls.impl
