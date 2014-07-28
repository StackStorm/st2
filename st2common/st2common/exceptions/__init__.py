class StackStormBaseException(Exception):
    """
        The root of the exception class hierarchy for all
        StackStorm server exceptions.

        For exceptions raised by plug-ins, see StackStormPluginException
        class.
    """
    pass


class StackStormPluginException(StackStormBaseException):
    """
        The root of the exception class hierarchy for all
        exceptions that are defined as part of a StackStorm
        plug-in API.

        It is recommended that each API define a root exception
        class for the API. This root exception class for the
        API should inherit from the StackStormPluginException
        class.
    """
    pass
