from st2common.exceptions import StackStormBaseException


class StackStormDBObjectNotFoundError(StackStormBaseException):
    pass

class StackStormDBObjectMalformedError(StackStormBaseException):
    pass
