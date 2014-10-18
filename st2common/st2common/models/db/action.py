import datetime
import mongoengine as me

from st2common import log as logging
from st2common.models.db import MongoDBAccess
from st2common.models.db.stormbase import StormFoundationDB, StormBaseDB, EscapedDynamicField


__all__ = ['RunnerTypeDB',
           'ActionDB',
           'ActionExecutionDB']


LOG = logging.getLogger(__name__)

PACK_SEPARATOR = '.'


class RunnerTypeDB(StormBaseDB):
    """
    The representation of an RunnerType in the system. An RunnerType
    has a one-to-one mapping to a particular ActionRunner implementation.

    Attributes:
        id: See StormBaseAPI
        name: See StormBaseAPI
        description: See StormBaseAPI
        enabled: A flag indicating whether the runner for this type is enabled.
        runner_module: The python module that implements the action runner for this type.
        runner_parameters: The specification for parameters for the action runner.
        required_parameters: The list of parameters required by the action runner.
    """

    enabled = me.BooleanField(
        required=True, default=True,
        help_text='A flag indicating whether the runner for this type is enabled.')
    runner_module = me.StringField(
        required=True,
        help_text='The python module that implements the action runner for this type.')
    runner_parameters = me.DictField(
        help_text='The specification for parameters for the action runner.')
    required_parameters = me.ListField(
        help_text='The list of parameters required by the action runner.')


class ActionDB(StormFoundationDB):
    """
    The system entity that represents a Stack Action/Automation in the system.

    Attribute:
        enabled: A flag indicating whether this action is enabled in the system.
        entry_point: The entry point to the action.
        runner_type: The actionrunner is used to execute the action.
        parameters: The specification for parameters for the action.
        required_parameters: The list of parameters required by the action.
    """
    name = me.StringField(required=True)
    description = me.StringField()
    enabled = me.BooleanField(
        required=True, default=True,
        help_text='A flag indicating whether the action is enabled.')
    entry_point = me.StringField(
        required=True,
        help_text='The entry point to the action.')
    content_pack = me.StringField(
        required=True,
        help_text='Name of the content pack.',
        unique_with='name')
    runner_type = me.DictField(
        required=True, default={},
        help_text='The action runner to use for executing the action.')
    parameters = me.DictField(
        help_text='The specification for parameters for the action.')
    required_parameters = me.ListField(
        help_text='The list of parameters required by the action.')


class ActionReference(object):
    def __init__(self, pack=None, name=None, ref=None):
        self.ref = ref
        self.name = name
        self.pack = pack

        if ref is not None:
            self.ref = ref
            self.pack = self.get_pack(self.ref)
            self.name = self.get_name(self.ref)
        else:
            self.ref = self.reference(pack=pack, name=name)

    @staticmethod
    def reference(pack=None, name=None):
        if pack and name:
            if PACK_SEPARATOR in pack:
                raise Exception('Pack name should not contain "%s"', PACK_SEPARATOR)
            return PACK_SEPARATOR.join([pack, name])
        else:
            raise Exception('Both pack and name needed for building ref. pack=%s, name=%s', pack,
                            name)

    @staticmethod
    def get_pack(ref):
        return ref.split(PACK_SEPARATOR, 1)[0]

    @staticmethod
    def get_name(ref):
        return ref.split(PACK_SEPARATOR, 1)[1]


class ActionExecutionDB(StormFoundationDB):
    """
        The databse entity that represents a Stack Action/Automation in
        the system.

        Attributes:
            status: the most recently observed status of the execution.
                    One of "starting", "running", "completed", "error".
            result: an embedded document structure that holds the
                    output and exit status code from the action.
    """

    # TODO: Can status be an enum at the Mongo layer?
    status = me.StringField(
        required=True,
        help_text='The current status of the ActionExecution.')
    start_timestamp = me.DateTimeField(
        default=datetime.datetime.utcnow,
        help_text='The timestamp when the ActionExecution was created.')
    ref = me.StringField(
        required=True,
        help_text='Reference to the action that has to be executed.')
    parameters = me.DictField(
        default={},
        help_text='The key-value pairs passed as to the action runner &  execution.')
    result = EscapedDynamicField(
        default={},
        help_text='Action defined result.')
    context = me.DictField(
        default={},
        help_text='Contextual information on the action execution.')
    callback = me.DictField(
        default={},
        help_text='Callback information for the on completion of action execution.')


# specialized access objects
runnertype_access = MongoDBAccess(RunnerTypeDB)
action_access = MongoDBAccess(ActionDB)
actionexec_access = MongoDBAccess(ActionExecutionDB)

MODELS = [RunnerTypeDB, ActionDB, ActionExecutionDB]
