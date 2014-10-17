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
from st2common.util import action_db as action_utils

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
        'action_name': 'action__name',
        'action_pack': 'action__content_pack',
        'action_id': 'action__id'
    }

    options = {
        'sort': ['action_pack', 'action_name']
    }

    @staticmethod
    def _get_action_executions(**kw):
        action_id = kw.get('action_id', None)
        action_name = kw.get('action_name', None)
        action_pack = kw.get('action_pack', None)
        limit = int(kw.get('limit', 50))

        if action_id is not None:
            LOG.debug('Using action_id=%s to get action executions', action_id)
            # action__id <- this queries action.id
            return ActionExecution.query(action__id=action_id,
                                         order_by=['-start_timestamp'],
                                         limit=limit)
        elif action_name is not None:
            if not action_pack:
                msg = 'Action has to be referred by id or a name + pack combination. Only name ' + \
                      'provided.'
                abort(http_client.BAD_REQUEST, msg)
            LOG.debug('Using action_name=%s and action_pack=%s to get action executions',
                      action_name, action_pack)
            results = ActionExecution.query(action__name=action_name,
                                            action__content_pack=action_pack,
                                            order_by=['-start_timestamp'],
                                            limit=limit)
            return results
        LOG.debug('Retrieving all action executions')
        return ActionExecution.get_all(order_by=['-start_timestamp'],
                                       limit=limit)

    @jsexpose()
    def get_all(self, **kw):
        """
            List all actionexecutions.

            Handles requests:
                GET /actionexecutions/
        """
        LOG.info('GET all /actionexecutions/ with filters=%s', kw)

        actionexec_dbs = ActionExecutionsController._get_action_executions(**kw)
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

            if not execution.action.get('id', None):
                action_db, _ = action_utils.get_action_by_dict({
                    'name': execution.action['name'],
                    'content_pack': execution.action['content_pack']})
                execution.action['id'] = str(action_db.id)

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
