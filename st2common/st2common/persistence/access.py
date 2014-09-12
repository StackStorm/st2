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

    @classmethod
    def add_or_update(kls, model_object, publish=True):
        if not getattr(model_object, 'user', None):
            raise ValueError('User is not provided in the token.')
        if not getattr(model_object, 'token', None):
            raise ValueError('Token value is not set.')
        if not getattr(model_object, 'expiry', None):
            raise ValueError('Token expiry is not provided in the token.')
        return super(Token, kls).add_or_update(model_object, publish=publish)
