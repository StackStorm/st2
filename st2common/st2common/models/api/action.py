from wsme import types as wtypes

from st2common.models.api.stormbase import BaseAPI

__all__ = ['StactionAPI',
           'StactionExecutionAPI',
           ]


class StactionAPI(BaseAPI):
    """The system entity that represents a Stack Action/Automation in
       the system.
    Attribute:
        enabled: flag indicating whether this staction is enabled in the system.
        repo_path: relative path to the staction artifact. Relative to the root
                   of the repo.
        run_type: string identifying which stactionrunner is used to execute the staction.
        parameter_names: flat list of strings required as key names when running
                   the staction.
    """
    enabled = wtypes.bool
    repo_path = wtypes.text
    run_type = wtypes.text
    parameter_names = wtypes.ArrayType(wtypes.text)
