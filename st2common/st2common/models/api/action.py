from wsme import types as wstypes

from st2common.models.api.stormbase import BaseAPI

__all__ = ['StactionAPI',
           'StactionExecutionAPI',
           ]


class ActionAPI(BaseAPI):
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
    # TODO: debug wsme+pecan problem with "bool"
    #enabled = wstypes.bool
    repo_path = wstypes.text
    run_type = wstypes.text
    parameter_names = wstypes.ArrayType(wstypes.text)

    @classmethod
    def from_model(cls, model):
        action = cls()
        action.id = str(model.id)
