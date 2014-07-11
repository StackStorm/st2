import datetime
from wsme import types as wstypes

from st2common import log as logging
from st2common.models.api.stormbase import (StormFoundationAPI, StormBaseAPI)
from st2common.models.db.action import (ActionDB, ActionExecutionDB)

__all__ = ['ActionAPI',
           'ActionExecutionAPI',
           ]


LOG = logging.getLogger(__name__)


class ActionAPI(StormBaseAPI):
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

    enabled = bool
    artifact_paths = wstypes.ArrayType(str)
    entry_point = wstypes.text
    runner_type = wstypes.text
    # TODO: Support default parameter values
    parameters = wstypes.DictType(str, str)

    @classmethod
    def from_model(kls, model):
        LOG.debug('entering ActionAPI.from_model() Input object: %s', model)

        action = StormBaseAPI.from_model(kls, model)
        action.enabled = bool(model.enabled)
        action.artifact_paths = [str(v) for v in model.artifact_paths]
        action.entry_point = str(model.entry_point)
        action.runner_type = str(model.runner_type)
        action.parameters = dict(model.parameters)
        LOG.debug('exiting ActionAPI.from_model() Result object: %s', action)
        return action

    @classmethod
    def to_model(kls, action):
        LOG.debug('entering ActionAPI.to_model() Input object: %s', action)

        model = StormBaseAPI.to_model(ActionDB, action)
        model.enabled = bool(action.enabled)
        model.artifact_paths = [str(v) for v in action.artifact_paths]
        model.entry_point = str(action.entry_point)
        model.runner_type = str(action.runner_type)
        model.parameters = dict(action.parameters)

        LOG.debug('exiting ActionAPI.to_model() Result object: %s', model)
        return model

    def __str__(self):
        # Note: List append followed by list comprehension is fastest way to build a string.
        result = []
        result.append('ActionAPI@')
        result.append(str(id(self)))
        result.append('(')
        result.append('id="%s", ' % self.id)
        result.append('name="%s", ' % self.name)
        result.append('description="%s", ' % self.description)
        result.append('enabled="%s",' % self.enabled)
        result.append('artifact_paths="%s",' % str(self.artifact_paths))
        result.append('entry_point="%s",' % self.entry_point)
        result.append('runner_type="%s",' % self.runner_type)
        result.append('parameters="%s",' % str(self.parameters))
        result.append('uri="%s")' % self.uri)
        return ''.join(result)


ACTIONEXEC_STATUS_INIT = 'initializing'
ACTIONEXEC_STATUS_RUNNING = 'running'
ACTIONEXEC_STATUS_COMPLETE = 'complete'
ACTIONEXEC_STATUS_ERROR = 'error'

ACTIONEXEC_STATUSES = [ACTIONEXEC_STATUS_INIT, ACTIONEXEC_STATUS_RUNNING,
                       ACTIONEXEC_STATUS_COMPLETE, ACTIONEXEC_STATUS_ERROR,
                       ]

ACTION_NAME = 'name'
ACTION_ID = 'id'


class ActionExecutionAPI(StormFoundationAPI):
    """The system entity that represents the execution of a Stack Action/Automation in
       the system.
    Attribute:
       ...
    """

    # Correct parameters...
    status = wstypes.Enum(str, *ACTIONEXEC_STATUSES)
    start_timestamp = datetime.datetime
    action = wstypes.DictType(str, str)
    runner_parameters = wstypes.DictType(str, str)
    action_parameters = wstypes.DictType(str, str)
    # result_data = wstypes.DictType(str, wstypes.DictType(str, str))
    exit_code = wstypes.text
    std_out = wstypes.text
    std_err = wstypes.text

    @classmethod
    def from_model(kls, model):
        LOG.debug('entering ActionExecutionAPI.from_model() Input object: %s', model)
        actionexec = StormFoundationAPI.from_model(kls, model)
        actionexec.action = dict(model.action)
        actionexec.status = str(model.status)
        actionexec.start_timestamp = model.start_timestamp
        actionexec.runner_parameters = dict(model.runner_parameters)
        actionexec.action_parameters = dict(model.action_parameters)
        # actionexec.result_data = dict(model.result_data)
        # if actionexec.exit_code not in [None, Unset]:
        #    actionexec.exit_code = int(model.exit_code)
        actionexec.exit_code = str(model.exit_code)
        actionexec.std_out = str(model.std_out)
        actionexec.std_err = str(model.std_err)
        LOG.debug('exiting ActionExecutionAPI.from_model() Result object: %s', actionexec)
        return actionexec

    @classmethod
    def to_model(kls, actionexec):
        LOG.debug('entering ActionExecutionAPI.to_model() Input object: %s', actionexec)
        model = StormFoundationAPI.to_model(ActionExecutionDB, actionexec)
        model.status = str(actionexec.status)
        model.start_timestamp = actionexec.start_timestamp
        model.action = actionexec.action
        model.runner_parameters = dict(actionexec.runner_parameters)
        model.action_parameters = dict(actionexec.action_parameters)
        # model.result_data = actionexec.result_data
        model.exit_code = str(actionexec.exit_code)
        model.std_out = str(actionexec.std_out)
        model.std_err = str(actionexec.std_err)
        LOG.debug('exiting ActionExecutionAPI.to_model() Result object: %s', model)
        return model

    def __str__(self):
        result = []
        result.append('ActionExecutionAPI@')
        result.append(str(id(self)))
        result.append('(')
        result.append('id="%s", ' % self.id)
        result.append('status="%s", ' % self.status)
        result.append('action="%s", ' % self.action)
        result.append('runner_parameters="%s", ' % self.runner_parameters)
        result.append('action_parameters="%s", ' % self.action_parameters)
        # result.append('result_data=%s, ' % json.dumps(self.result_data))
        result.append('exit_code="%s", ' % self.exit_code)
        result.append('std_out="%s", ' % self.std_out)
        result.append('std_err="%s", ' % self.std_err)
        result.append('uri="%s")' % self.uri)
        return ''.join(result)
