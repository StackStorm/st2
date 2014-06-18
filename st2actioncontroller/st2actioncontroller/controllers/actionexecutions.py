import httplib
from pecan import (abort, expose, response)
from pecan.rest import RestController

# TODO: Encapsulate mongoengine errors in our persistence layer. Exceptions
#       that bubble up to this layer should be core Python exceptions or
#       StackStorm defined exceptions.
from mongoengine import ValidationError

from wsme import types as wstypes
import wsmeext.pecan as wsme_pecan

from st2common import log as logging
from st2common.persistence.action import ActionExecution
from st2common.models.api.action import ActionExecutionAPI


LOG = logging.getLogger('st2actioncontroller')


class ActionExecutionsController(RestController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of ActionExecutions in the system.
    """

    def get_by_id(self, id):
        """
            Get ActionExecution by id and abort http operation on errors.
        """
        try:
            actionexec = ActionExecution.get_by_id(id)
        except (ValidationError, ValueError) as e:
            LOG.error('Database lookup for id="%s" resulted in exception: %s', id, e)
            abort(httplib.NOT_FOUND)
        
        return actionexec

    @wsme_pecan.wsexpose(ActionExecutionAPI, wstypes.text)
    def get_one(self, id):
        """
            List actionexecution by id.

            Handle:
                GET /actionexecutions/1
        """

        LOG.info('GET /actionexecutions/ with id="%s"', id)

        actionexec_db = self.get_by_id(id)
        actionexec_api = ActionExecutionAPI.from_model(actionexec_db)

        LOG.debug('GET /actionexecutions/ with id=%s, client_result=%s', id, actionexec_api)
        return actionexec_api

    # TODO: Support kwargs
    @wsme_pecan.wsexpose([ActionExecutionAPI])
    def get_all(self):
        """
            List all actionexecutions.

            Handles requests:
                GET /actionexecutions/
        """

        LOG.info('GET all /actionexecutions/')
        actionexec_apis = [ActionExecutionAPI.from_model(actionexec_db)
                                for actionexec_db in ActionExecution.get_all()]

        # TODO: unpack list in log message
        LOG.debug('GET all /actionexecutions/ client_result=%s', actionexec_apis)
        return actionexec_apis

    @wsme_pecan.wsexpose(ActionExecutionAPI, body=ActionExecutionAPI,
                            status_code=httplib.CREATED)
    def post(self, data):
        """
            Create a new actionexecution.

            Handles requests:
                POST /actionexecutions/
        """

        LOG.info('POST /actionexecutions/ with actionexec data=%s', data)

        actionexec_api = ActionExecutionAPI.to_model(data)
        LOG.debug('/actionexecutions/ POST verified ActionExecutionAPI object=%s',
                    actionexec_api)
        # TODO: POST operations should only add to DB.
        #       If an existing object conflicts then raise an error.

        actionexec_db = ActionExecution.add_or_update(actionexec_api)
        LOG.debug('/actionexecutions/ POST saved ActionExecutionDB object=%s', actionexec_db)
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

        # TODO: Support delete by name
        LOG.info('DELETE /actionexecutions/ with id=%s', id)

        actionexec_db = self.get_by_id(id)
        LOG.debug('DELETE /actionexecutions/ lookup with id=%s found object: %s', 
                    id, actionexec_db)

        # TODO: Delete should migrate the execution data to a history collection.

        try:
            ActionExecution.delete(actionexec_db)
        except Exception, e:
            LOG.error('Database delete encountered exception during delete of id="%s". Exception was %s', id, e)

        LOG.info('DELETE /actionexecutions/ with id="%s" completed', id)
        return None
