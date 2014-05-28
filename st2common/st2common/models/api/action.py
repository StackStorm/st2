from wsme import types as wstypes

from st2common.models.api.stormbase import BaseAPI

__all__ = ['ActionAPI',
           'ActionExecutionAPI',
           ]


class ActionAPI(BaseAPI):
    """The system entity that represents a Stack Action/Automation in
       the system.
    Attribute:
        enabled: flag indicating whether this action is enabled in the system.
        repo_path: relative path to the action artifact. Relative to the root
                   of the repo.
        run_type: string identifying which actionrunner is used to execute the action.
        parameter_names: flat list of strings required as key names when running
                   the action.
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
