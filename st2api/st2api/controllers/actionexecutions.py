import json

import jsonschema
import pecan
from pecan import abort
from six.moves import http_client

from st2api.controllers.resource import ResourceController
from st2common import log as logging
from st2common.models.api.action import ActionExecutionAPI
from st2common.models.base import jsexpose
from st2common.persistence.action import ActionExecution
from st2common.services import action as action_service

LOG = logging.getLogger(__name__)


MONITOR_THREAD_EMPTY_Q_SLEEP_TIME = 5
MONITOR_THREAD_NO_WORKERS_SLEEP_TIME = 1


class ActionExecutionsController(ResourceController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of ActionExecutions in the system.
    """
    model = ActionExecutionAPI
    access = ActionExecution

    supported_filters = {
        'action': 'action'
    }

    query_options = {
        'sort': ['-start_timestamp', 'action']
    }

    def _get_action_executions(self, **kw):
        kw['limit'] = int(kw.get('limit', 50))

        LOG.debug('Retrieving all action executions with filters=%s', kw)
        return super(ActionExecutionsController, self)._get_all(**kw)

    @jsexpose()
    def get_all(self, **kw):
        """
            List all actionexecutions.

            Handles requests:
                GET /actionexecutions/
        """
        LOG.info('GET all /actionexecutions/ with filters=%s', kw)
        return self._get_action_executions(**kw)

    @jsexpose(body=ActionExecutionAPI, status_code=http_client.CREATED)
    def post(self, execution):
        try:
            # Initialize execution context if it does not exist.
            if not hasattr(execution, 'context'):
                execution.context = dict()

            # Retrieve user context from the request header.
            execution.context['user'] = pecan.request.headers.get('X-User-Name')

            # Retrieve other st2 context from request header.
            if ('st2-context' in pecan.request.headers and pecan.request.headers['st2-context']):
                context = pecan.request.headers['st2-context'].replace("'", "\"")
                execution.context.update(json.loads(context))

            # Schedule the action execution.
            executiondb = ActionExecutionAPI.to_model(execution)
            executiondb = action_service.schedule(executiondb)
            return ActionExecutionAPI.from_model(executiondb)
        except ValueError as e:
            LOG.exception('Unable to execute action.')
            abort(http_client.BAD_REQUEST, str(e))
        except jsonschema.ValidationError as e:
            LOG.exception('Unable to execute action. Parameter validation failed.')
            abort(http_client.BAD_REQUEST, str(e))
        except Exception as e:
            LOG.exception('Unable to execute action. Unexpected error encountered.')
            abort(http_client.INTERNAL_SERVER_ERROR, str(e))

    @jsexpose(str, body=ActionExecutionAPI)
    def put(self, id, actionexecution):
        try:
            actionexec_db = ActionExecution.get_by_id(id)
        except:
            msg = 'ActionExecution by id: %s not found.' % id
            pecan.abort(http_client, msg)
        new_actionexec_db = ActionExecutionAPI.to_model(actionexecution)
        if actionexec_db.status != new_actionexec_db.status:
            actionexec_db.status = new_actionexec_db.status
        if actionexec_db.result != new_actionexec_db.result:
            actionexec_db.result = new_actionexec_db.result
        actionexec_db = ActionExecution.add_or_update(actionexec_db)
        actionexec_api = ActionExecutionAPI.from_model(actionexec_db)
        return actionexec_api

    @jsexpose()
    def options(self):
        return
