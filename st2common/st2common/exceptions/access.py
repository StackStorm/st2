from st2common.exceptions import StackStormBaseException
from st2common.exceptions.db import StackStormDBObjectNotFoundError


class TokenNotProvidedError(StackStormBaseException):
    pass


class TokenNotFoundError(StackStormDBObjectNotFoundError):
    pass


class TokenExpiredError(StackStormBaseException):
    pass
