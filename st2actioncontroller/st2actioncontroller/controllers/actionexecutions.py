import datetime
import httplib
import json
from pecan import abort
from pecan.rest import RestController

# TODO: Encapsulate mongoengine errors in our persistence layer. Exceptions
#       that bubble up to this layer should be core Python exceptions or
#       StackStorm defined exceptions.

import requests

from wsme import types as wstypes
from wsme import Unset
import wsmeext.pecan as wsme_pecan

from st2common import log as logging
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.util.http import HTTP_SUCCESS
from st2common.persistence.action import ActionExecution
from st2common.models.api.action import (ActionExecutionAPI,
                                         ACTIONEXEC_STATUS_INIT,
                                         ACTIONEXEC_STATUS_ERROR)
from st2common.util.action_db import (get_action_by_dict, get_actionexec_by_id,
                                      update_actionexecution_status)


LOG = logging.getLogger(__name__)


LIVEACTION_ENDPOINT = 'http://localhost:9501/liveactions'


class ActionExecutionsController(RestController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of ActionExecutions in the system.
    """

    def _issue_liveaction_delete(self, actionexec_id):
        """
            Destroy the LiveActions specified by actionexec_id by performing
            a DELETE against the /liveactions/ http endpoint.
        """
        LOG.info('Issuing /liveactions/ DELETE for ActionExecution with id="%s"', actionexec_id)
        request_error = False
        result = None
        try:
            result = requests.delete(LIVEACTION_ENDPOINT +
                                     '/?actionexecution_id=' + str(actionexec_id))
        except requests.exceptions.ConnectionError as e:
            LOG.error('Caught encoundered connection error while performing /liveactions/ '
                      'DELETE for actionexec_id="%s".'
                      'Error was: %s', actionexec_id, e)
            request_error = True

        LOG.debug('/liveactions/ DELETE request result: %s', result)

        return(result, request_error)

    def _issue_liveaction_post(self, actionexec_id):
        """
            Launch the ActionExecution specified by actionexec_id by performing
            a POST against the /liveactions/ http endpoint.
        """

        custom_headers = self._create_custom_headers()
        payload = self._create_liveaction_data(actionexec_id)
        LOG.info('Payload for /liveactions/ POST: data="%s" custom_headers="%s"',
                 payload, custom_headers)
        LOG.info('Issuing /liveactions/ POST for ActionExecution with id ="%s"', actionexec_id)

        request_error = False
        result = None
        try:
            result = requests.post(LIVEACTION_ENDPOINT,
                                   data=json.dumps(payload), headers=custom_headers)
        except requests.exceptions.ConnectionError as e:
            LOG.error('Caught encoundered connection error while performing /liveactions/ POST.'
                      'Error was: %s', e)
            request_error = True

        LOG.debug('/liveactions/ POST request result: %s', result)

        return(result, request_error)

    @staticmethod
    def _get_action_executions(action_id, action_name, limit=None):
        if action_id is not None:
            LOG.debug('Using action_id=%s to get action executions', action_id)
            # action__id <- this queries action.id
            return ActionExecution.query(action__id=action_id,
                                         order_by=['-start_timestamp'],
                                         limit=limit)
        elif action_name is not None:
            LOG.debug('Using action_name=%s to get action executions', action_name)
            # action__name <- this queries against action.name
            return ActionExecution.query(action__name=action_name,
                                         order_by=['-start_timestamp'],
                                         limit=limit)
        LOG.debug('Retrieving all action executions')
        return ActionExecution.get_all(order_by=['-start_timestamp'],
                                       limit=limit)

    def _create_custom_headers(self):
        return {'content-type': 'application/json'}

    def _create_liveaction_data(self, actionexecution_id):
        return {'actionexecution_id': str(actionexecution_id)}

    @wsme_pecan.wsexpose(ActionExecutionAPI, wstypes.text)
    def get_one(self, id):
        """
            List actionexecution by id.

            Handle:
                GET /actionexecutions/1
        """

        LOG.info('GET /actionexecutions/ with id="%s"', id)

        try:
            actionexec_db = get_actionexec_by_id(id)
        except StackStormDBObjectNotFoundError as e:
            LOG.error('GET /actionexecutions/ with id="%s": %s', id, e.message)
            abort(httplib.NOT_FOUND)

        actionexec_api = ActionExecutionAPI.from_model(actionexec_db)

        LOG.debug('GET /actionexecutions/ with id=%s, client_result=%s', id, actionexec_api)
        return actionexec_api

    @wsme_pecan.wsexpose([ActionExecutionAPI], wstypes.text,
                         wstypes.text, wstypes.text)
    def get_all(self, action_id=None, action_name=None, limit='50'):
        """
            List all actionexecutions.

            Handles requests:
                GET /actionexecutions/
        """

        LOG.info('GET all /actionexecutions/ with action_name=%s, '
                 'action_id=%s, and limit=%s', action_name, action_id, limit)

        actionexec_dbs = ActionExecutionsController._get_action_executions(
            action_id, action_name, limit=int(limit))
        actionexec_apis = [ActionExecutionAPI.from_model(actionexec_db)
                           for actionexec_db
                           in sorted(actionexec_dbs,
                                     key=lambda x: x.start_timestamp)]

        # TODO: unpack list in log message
        LOG.debug('GET all /actionexecutions/ client_result=%s', actionexec_apis)
        return actionexec_apis

    @wsme_pecan.wsexpose(ActionExecutionAPI, body=ActionExecutionAPI,
                         status_code=httplib.CREATED)
    def post(self, actionexecution):
        """
            Create a new actionexecution.

            Handles requests:
                POST /actionexecutions/
        """

        LOG.info('POST /actionexecutions/ with actionexec data=%s', actionexecution)

        actionexecution.start_timestamp = datetime.datetime.now()

        # Fill-in runner_parameters and action_parameter fields if they are not
        # provided in the request.
        if actionexecution.parameters is Unset:
            LOG.warning('POST /actionexecutions/ request did not '
                        'provide parameters field.')
            actionexecution.runner_parameters = {}

        (action_db, action_dict) = get_action_by_dict(actionexecution.action)
        if not action_db:
            LOG.error('POST /actionexecutions/ Action for "%s" cannot be found.',
                      actionexecution.action)
            abort(httplib.INTERNAL_SERVER_ERROR)
        else:
            if action_dict != dict(actionexecution.action):
                LOG.info('POST /actionexecutions/ Action identity dict updated to remove '
                         'lookup failure.')
                actionexecution.action = action_dict

        # If the Action is disabled, abort the POST call.
        if not action_db.enabled:
            LOG.error('POST /actionexecutions/ Unable to create Action Execution for a disabled '
                      'Action. Action is: %s', action_db)
            abort(httplib.FORBIDDEN)

        # Set initial value for ActionExecution status.
        # Not using update_actionexecution_status to allow other initialization to
        # be done before saving to DB.
        LOG.debug('Setting actionexecution status to "%s"', ACTIONEXEC_STATUS_INIT)
        actionexecution.status = ACTIONEXEC_STATUS_INIT

        LOG.info('POST /actionexecutions/ with actionexec data=%s', actionexecution)
        actionexec_api = ActionExecutionAPI.to_model(actionexecution)
        LOG.debug('/actionexecutions/ POST verified ActionExecutionAPI object=%s',
                  actionexec_api)

        # TODO: POST operations should only add to DB.
        #       If an existing object conflicts then raise an error.

        LOG.audit('ActionExecution requested. '
                  'ActionExecution about to be created in database.'
                  'ActionExecution is: %s', actionexec_api)
        actionexec_db = ActionExecution.add_or_update(actionexec_api)
        LOG.debug('/actionexecutions/ POST saved ActionExecution object=%s', actionexec_db)

        LOG.audit('Received a request  to execute an Action. '
                  'ActionExecution created in the database. '
                  'ActionExecution is: %s', actionexec_db)

        actionexec_id = actionexec_db.id
        (result, request_error) = self._issue_liveaction_post(actionexec_id)

        if (not request_error) and (result.status_code in HTTP_SUCCESS):
            LOG.info('/liveactions/ POST request reported successful creation of LiveAction')
            # TODO: This should be "running status, or "scheduled" status when execution is async
            # actionexec_status = ACTIONEXEC_STATUS_COMPLETE

            # Update actionexec_db status.
            # With side-effect of re-loading ActionExecution from DB.
            # LOG.info('/actionexecutions/ POST update ActionExecution in DB after '
            #         'LiveAction POST: %s', actionexec_db)
            # actionexec_db = update_actionexecution_status(actionexec_status,
            #                                              actionexec_id=actionexec_id)

            actionexec_db = get_actionexec_by_id(actionexec_db.id)
        else:
            LOG.info('/liveactions/ POST request reported error: %s', result.status_code)
            actionexec_status = ACTIONEXEC_STATUS_ERROR

            # Update actionexec_db status.
            LOG.info('/actionexecutions/ POST update ActionExecution in DB after '
                     'LiveAction POST: %s', actionexec_db)
            actionexec_db = update_actionexecution_status(actionexec_status,
                                                          actionexec_id=actionexec_id)
            LOG.error('Unable to launch LiveAction.')
            LOG.info('Aborting /actionexecutions/ POST operation.')
            abort(httplib.INTERNAL_SERVER_ERROR)

        actionexec_api = ActionExecutionAPI.from_model(actionexec_db)

        LOG.debug('POST /actionexecutions/ client_result=%s', actionexec_api)
        return actionexec_api

    @wsme_pecan.wsexpose(ActionExecutionAPI, body=ActionExecutionAPI,
                         status_code=httplib.FORBIDDEN)
    def put(self, data):
        """
            Update an actionexecution does not make any sense.

            Handles requests:
                POST /actionexecutions/1?_method=put
                PUT /actionexecutions/1
        """
        return None

    @wsme_pecan.wsexpose(None, wstypes.text, status_code=httplib.NO_CONTENT)
    def delete(self, id):
        """
            Delete an actionexecution.

            Handles requests:
                POST /actionexecutions/1?_method=delete
                DELETE /actionexecutions/1
        """

        LOG.info('DELETE /actionexecutions/ with id=%s', id)

        try:
            actionexec_db = get_actionexec_by_id(id)
        except StackStormDBObjectNotFoundError as e:
            LOG.error('DELETE /actionexecutions/ with id="%s": %s', id, e.message)
            abort(httplib.NOT_FOUND)

        LOG.debug('DELETE /actionexecutions/ lookup with id=%s found object: %s',
                  id, actionexec_db)

        # TODO: Delete should migrate the execution data to a history collection.

        (result, request_error) = self._issue_liveaction_delete(actionexec_db.id)
        # TODO: Validate that liveactions for actionexec are all deleted.
        if request_error:
            LOG.warning('DELETE of Live Actions for actionexecution_id="%s" encountered '
                        'an error. HTTP result is: %s', actionexec_db.id, result)

        try:
            ActionExecution.delete(actionexec_db)
        except Exception as e:
            LOG.error('Database delete encountered exception during delete of id="%s". '
                      'Exception was %s', id, e)

        LOG.audit('ActionExecution was deleted from database. '
                  'The ActionExecution was: "%s', actionexec_db)

        LOG.info('DELETE /actionexecutions/ with id="%s" completed', id)
        return None
