from st2common.persistence import Access
from st2common.models.db import MongoDBAccess
from st2common.models.db.access import UserDB, TokenDB


class User(Access):
    IMPL = MongoDBAccess(UserDB)


class Token(Access):
    IMPL = MongoDBAccess(TokenDB)
