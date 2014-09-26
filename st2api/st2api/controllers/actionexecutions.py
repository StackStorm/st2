import json
import datetime

import jsonschema
import pecan
from pecan import abort
from pecan.rest import RestController
from six.moves import http_client

from st2common import log as logging
from st2common.models.base import jsexpose
from st2common.services import action as action_service
from st2common.persistence.action import ActionExecution
from st2common.models.api.action import ActionExecutionAPI


LOG = logging.getLogger(__name__)


MONITOR_THREAD_EMPTY_Q_SLEEP_TIME = 5
MONITOR_THREAD_NO_WORKERS_SLEEP_TIME = 1


class ActionExecutionsController(RestController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of ActionExecutions in the system.
    """

    @staticmethod
    def __get_by_id(id):
        try:
            return ActionExecution.get_by_id(id)
        except Exception as e:
            msg = 'Database lookup for id="%s" resulted in exception. %s' % (id, e)
            LOG.exception(msg)
            abort(http_client.NOT_FOUND, msg)

    @staticmethod
    def _get_action_executions(action_id, action_name, limit=None, **kw):
        if action_id is not None:
            LOG.debug('Using action_id=%s to get action executions', action_id)
            # action__id <- this queries action.id
            return ActionExecution.query(action__id=action_id,
                                         order_by=['-start_timestamp'],
                                         limit=limit, **kw)
        elif action_name is not None:
            LOG.debug('Using action_name=%s to get action executions', action_name)
            # action__name <- this queries against action.name
            return ActionExecution.query(action__name=action_name,
                                         order_by=['-start_timestamp'],
                                         limit=limit, **kw)
        LOG.debug('Retrieving all action executions')
        return ActionExecution.get_all(order_by=['-start_timestamp'],
                                       limit=limit, **kw)

    @jsexpose(str)
    def get_one(self, id):
        """
            List actionexecution by id.

            Handle:
                GET /actionexecutions/1
        """
        LOG.info('GET /actionexecutions/ with id=%s', id)
        actionexec_db = ActionExecutionsController.__get_by_id(id)
        actionexec_api = ActionExecutionAPI.from_model(actionexec_db)
        LOG.debug('GET /actionexecutions/ with id=%s, client_result=%s', id, actionexec_api)
        return actionexec_api

    @jsexpose(str, str, str)
    def get_all(self, action_id=None, action_name=None, limit='50', **kw):
        """
            List all actionexecutions.

            Handles requests:
                GET /actionexecutions/
        """

        LOG.info('GET all /actionexecutions/ with action_name=%s, '
                 'action_id=%s, and limit=%s', action_name, action_id, limit)

        actionexec_dbs = ActionExecutionsController._get_action_executions(
            action_id, action_name, limit=int(limit), **kw)
        actionexec_apis = [ActionExecutionAPI.from_model(actionexec_db)
                           for actionexec_db
                           in sorted(actionexec_dbs,
                                     key=lambda x: x.start_timestamp)]

        # TODO: unpack list in log message
        LOG.debug('GET all /actionexecutions/ client_result=%s', actionexec_apis)
        return actionexec_apis

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
            return action_service.schedule(execution)
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
        actionexecution.start_timestamp = datetime.datetime.now()
        actionexec_db = ActionExecutionsController.__get_by_id(id)
        new_actionexec_db = ActionExecutionAPI.to_model(actionexecution)
        if actionexec_db.status != new_actionexec_db.status:
            actionexec_db.status = new_actionexec_db.status
        if actionexec_db.result != new_actionexec_db.result:
            actionexec_db.result = new_actionexec_db.result
        actionexec_db = ActionExecution.add_or_update(actionexec_db)
        actionexec_api = ActionExecutionAPI.from_model(actionexec_db)
        return actionexec_api
