from st2common.exceptions import StackStormPluginException


class ActionRunnerException(StackStormPluginException):
    pass


class ActionRunnerCreateError(ActionRunnerException):
    pass


class ActionRunnerDispatchError(ActionRunnerException):
    pass
