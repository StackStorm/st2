from st2common.exceptions import StackStormPluginException


class SensorPluginException(StackStormPluginException):
    pass


class TriggerTypeRegistrationException(SensorPluginException):
    pass
