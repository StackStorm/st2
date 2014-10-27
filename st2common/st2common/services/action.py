import datetime
import jsonschema
import six

from st2common import log as logging
from st2common.util import isotime
from st2common.util import action_db as action_utils
from st2common.util import schema as util_schema
from st2common.persistence.action import ActionExecution
from st2common.constants.action import ACTIONEXEC_STATUS_SCHEDULED

LOG = logging.getLogger(__name__)


def _get_immutable_params(parameters):
    if not parameters:
        return []
    return [k for k, v in six.iteritems(parameters) if v.get('immutable', False)]


def schedule(execution):

    # Use the user context from the parent action execution. Subtasks in a workflow
    # action can be invoked by a system user and so we want to use the user context
    # from the original workflow action.
    if getattr(execution, 'context', None) and 'parent' in execution.context:
        parent = ActionExecution.get_by_id(execution.context['parent'])
        execution.context['user'] = getattr(parent, 'context', dict()).get('user')

    # Validate action.
    action_db = action_utils.get_action_by_ref(execution.action)
    if not action_db:
        raise ValueError('Action "%s" cannot be found.' % execution.action)
    if not action_db.enabled:
        raise ValueError('Unable to execute. Action "%s" is disabled.' % execution.action)

    runnertype_db = action_utils.get_runnertype_by_name(action_db.runner_type['name'])

    if not hasattr(execution, 'parameters'):
        execution.parameters = dict()

    # Validate action parameters.
    schema = util_schema.get_parameter_schema(action_db)
    validator = util_schema.get_validator()
    jsonschema.validate(execution.parameters, schema, validator)

    # validate that no immutable params are being overriden. Although possible to
    # ignore the override it is safer to inform the user to avoid surprises.
    immutables = _get_immutable_params(action_db.parameters)
    immutables.extend(_get_immutable_params(runnertype_db.runner_parameters))
    overridden_immutables = [p for p in six.iterkeys(execution.parameters) if p in immutables]
    if len(overridden_immutables) > 0:
        raise ValueError('Override of immutable parameter(s) %s is unsupported.'
                         % str(overridden_immutables))

    # Write to database and send to message queue.
    execution.status = ACTIONEXEC_STATUS_SCHEDULED
    execution.start_timestamp = isotime.add_utc_tz(datetime.datetime.utcnow())
    execution = ActionExecution.add_or_update(execution)
    LOG.audit('Action execution scheduled. ActionExecution=%s.', execution)
    return execution
