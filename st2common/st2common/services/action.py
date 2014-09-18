import datetime

import six
import jsonschema

from st2common import log as logging
from st2common.util import action_db as db
from st2common.util import schema as util_schema
from st2common.persistence.action import ActionExecution
from st2common.models.api.action import ActionExecutionAPI, ACTIONEXEC_STATUS_SCHEDULED


LOG = logging.getLogger(__name__)


def schedule(execution):

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
        execution.runner_parameters = dict()

    # Assign default parameters.
    runnertype = db.get_runnertype_by_name(action_db.runner_type['name'])
    for key, metadata in six.iteritems(runnertype.runner_parameters):
        if key not in execution.parameters and 'default' in metadata:
            if metadata.get('default') is not None:
                execution.parameters[key] = metadata['default']

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
