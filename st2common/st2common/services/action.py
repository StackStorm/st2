import datetime

import jsonschema

from st2common import log as logging
from st2common.util import action_db as db
from st2common.util import schema as util_schema
from st2common.persistence.action import ActionExecution
from st2common.models.api.action import ActionExecutionAPI, ACTIONEXEC_STATUS_SCHEDULED


LOG = logging.getLogger(__name__)


def schedule(execution):

    # Use the user context from the parent action execution. Subtasks in a workflow
    # action can be invoked by a system user and so we want to use the user context
    # from the original workflow action.
    if getattr(execution, 'context', None) and 'parent' in execution.context:
        parent = ActionExecution.get_by_id(execution.context['parent'])
        execution.context['user'] = getattr(parent, 'context', dict()).get('user')

    # Validate action.
    (action_db, action_dict) = db.get_action_by_dict(execution.action)
    if not action_db:
        raise ValueError('Action "%s" cannot be found.' % execution.action)
    if not action_db.enabled:
        raise ValueError('Unable to execute. Action "%s" is disabled.' % execution.action)
    execution.action = action_dict

    # Populate runner and action parameters if parameters are not provided.
    if not hasattr(execution, 'parameters'):
        execution.parameters = dict()

    # Validate action parameters.
    schema = util_schema.get_parameter_schema(action_db)
    jsonschema.validate(execution.parameters, schema)

    # Write to database and send to message queue.
    execution.status = ACTIONEXEC_STATUS_SCHEDULED
    execution.start_timestamp = datetime.datetime.now()
    executiondb = ActionExecutionAPI.to_model(execution)
    executiondb = ActionExecution.add_or_update(executiondb)
    LOG.audit('Action execution scheduled. ActionExecution=%s.', executiondb)
    return ActionExecutionAPI.from_model(executiondb)
