import datetime
import json
from wsme import wsattr
from wsme import types as wstypes

from st2common import log as logging
from st2common.models.api.stormbase import (StormFoundationAPI, StormBaseAPI)
from st2common.models.db.action import (RunnerTypeDB, ActionDB, ActionExecutionDB)

__all__ = ['ActionAPI',
           'ActionExecutionAPI',
           'RunnerTypeAPI']


LOG = logging.getLogger(__name__)


class RunnerTypeAPI(StormBaseAPI):
    """
        The representation of an RunnerType in the system. An RunnerType
        has a one-to-one mapping to a particular ActionRunner implementation.

        Attributes:
            id: See StormBaseAPI
            name: See StormBaseAPI
            description: See StormBaseAPI

            enabled: Boolean value indicating whether the runner for this type
                     is enabled.
            runner_module: The python module that implements the action runner
                           for this type.
            runner_parameters: The names for the parameter that are required by the
                               action runner. Any values in this dictionary are
                               default values for the parameters.
    """
    enabled = bool
    runner_parameters = wstypes.DictType(str, str)
    runner_module = wstypes.text

    @classmethod
    def from_model(kls, model):
        LOG.debug('entering RctionTypeAPI.from_model() Input object: %s', model)

        runnertype = StormBaseAPI.from_model(kls, model)
        runnertype.enabled = bool(model.enabled)
        runnertype.runner_module = str(model.runner_module)
        runnertype.runner_parameters = dict(model.runner_parameters)

        LOG.debug('exiting RunnerTypeAPI.from_model() Result object: %s', runnertype)
        return runnertype

    @classmethod
    def to_model(kls, runnertype):
        LOG.debug('entering RunnerTypeAPI.to_model() Input object: %s', runnertype)

        model = StormBaseAPI.to_model(RunnerTypeDB, runnertype)
        model.enabled = bool(runnertype.enabled)
        model.runner_module = str(runnertype.runner_module)
        model.runner_parameters = dict(runnertype.runner_parameters)

        LOG.debug('exiting RunnerTypeAPI.to_model() Result object: %s', model)
        return model

    # TODO: Write generic str function for API and DB model base classes
    def __str__(self):
        result = []
        result.append('RunnerTypeAPI@')
        result.append(str(id(self)))
        result.append('(')
        result.append('id="%s", ' % self.id)
        result.append('name="%s", ' % self.name)
        result.append('description="%s", ' % self.description)
        result.append('enabled="%s", ' % self.enabled)
        result.append('runner_module="%s", ' % str(self.runner_module))
        result.append('runner_parameters="%s", ' % str(self.runner_parameters))
        result.append('uri="%s")' % self.uri)
        return ''.join(result)


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
    entry_point = wstypes.text
    runner_type = wstypes.text
    # TODO: Support default parameter values
    parameters = wstypes.DictType(str, str)

    @classmethod
    def from_model(kls, model):
        LOG.debug('entering ActionAPI.from_model() Input object: %s', model)

        action = StormBaseAPI.from_model(kls, model)
        action.enabled = bool(model.enabled)
        action.entry_point = str(model.entry_point)
        action.runner_type = str(model.runner_type.name)
        action.parameters = dict(model.runner_type.runner_parameters)
        action.parameters.update(model.parameters)
        LOG.debug('exiting ActionAPI.from_model() Result object: %s', action)
        return action

    @classmethod
    def to_model(kls, action, runnertype_db):
        LOG.debug('entering ActionAPI.to_model() Input object: %s', action)

        model = StormBaseAPI.to_model(ActionDB, action)
        model.enabled = bool(action.enabled)
        model.entry_point = str(action.entry_point)
        model.runner_type = runnertype_db
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
        result.append('entry_point="%s",' % self.entry_point)
        result.append('runner_type="%s",' % self.runner_type)
        result.append('parameters="%s",' % str(self.parameters))
        result.append('uri="%s")' % self.uri)
        return ''.join(result)


ACTIONEXEC_STATUS_INIT = 'initializing'
ACTIONEXEC_STATUS_SCHEDULED = 'scheduled'
ACTIONEXEC_STATUS_RUNNING = 'running'
ACTIONEXEC_STATUS_COMPLETE = 'complete'
ACTIONEXEC_STATUS_ERROR = 'error'

ACTIONEXEC_STATUSES = [ACTIONEXEC_STATUS_INIT, ACTIONEXEC_STATUS_SCHEDULED,
                       ACTIONEXEC_STATUS_RUNNING, ACTIONEXEC_STATUS_COMPLETE,
                       ACTIONEXEC_STATUS_ERROR]

ACTION_NAME = 'name'
ACTION_ID = 'id'


class ActionExecutionAPI(StormFoundationAPI):
    """The system entity that represents the execution of a Stack Action/Automation in
       the system.
    Attribute:
       ...
    """
    status = wstypes.Enum(str, *ACTIONEXEC_STATUSES)
    start_timestamp = datetime.datetime
    action = wsattr(wstypes.DictType(str, str), mandatory=True)
    parameters = wsattr(wstypes.DictType(str, str), default={})
    result = wsattr(str, default='')

    @classmethod
    def from_model(kls, model):
        LOG.debug('entering ActionExecutionAPI.from_model() Input object: %s', model)
        actionexec = StormFoundationAPI.from_model(kls, model)
        actionexec.action = dict(model.action)
        actionexec.status = str(model.status)
        actionexec.start_timestamp = model.start_timestamp
        actionexec.parameters = dict(model.parameters)
        actionexec.result = model.result
        LOG.debug('exiting ActionExecutionAPI.from_model() Result object: %s', actionexec)
        return actionexec

    @classmethod
    def to_model(kls, actionexec):
        LOG.debug('entering ActionExecutionAPI.to_model() Input object: %s', actionexec)
        model = StormFoundationAPI.to_model(ActionExecutionDB, actionexec)
        model.status = str(actionexec.status)
        model.start_timestamp = actionexec.start_timestamp
        model.action = actionexec.action
        model.parameters = dict(actionexec.parameters)
        model.result = actionexec.result
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
        result.append('parameters="%s", ' % self.parameters)
        result.append('result=%s, ' % json.dumps(self.result))
        result.append('uri="%s")' % self.uri)
        return ''.join(result)
