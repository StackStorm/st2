import httplib
import logging
from pecan import (abort, expose, response)
from pecan.rest import RestController

# TODO: Encapsulate mongoengine errors in our persistence layer. Exceptions
#       that bubble up to this layer should be core Python exceptions or
#       StackStorm defined exceptions.
from mongoengine import ValidationError

from wsme import types as wstypes
import wsmeext.pecan as wsme_pecan

from st2common.persistence.action import ActionExecution
from st2common.models.api.action import ActionExecutionAPI


LOG = logging.getLogger('st2actioncontroller')


class ActionExecutionsController(RestController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of ActionExecutions in the system.
    """

    @wsme_pecan.wsexpose(ActionExecutionAPI, wstypes.text)
    def get_one(self, id):
        """
            List actionexecution by id.

            Handle:
                GET /actionexecutions/1
        """

        LOG.info('GET /actionexecutions/ with id="%s"', id)
        actionexec_db = ActionExecution.get_by_id(id)

        # TODO: test/handle object not found.
        return ActionExecutionAPI.from_model(actionexec_db)

    @expose('json')
    def get_all(self):
        """
            List all actionexecutions.

            Handles requests:
                GET /actionexecutions/
        """

        # TODO: Implement function
        # TODO: Implement if=foo and name=bar based lookup to support query semantics.
        return {"dummy": "get_all"}

    @wsme_pecan.wsexpose(ActionExecutionAPI, body=ActionExecutionAPI)
    def post(self, actionexec):
        """
            Create a new actionexecution.

            Handles requests:
                POST /actionexecutions/
        """
        actionexec_db = ActionExecutionAPI.to_model(actionexec)
        # TODO: POST operations should only add to DB.
        # TODO: Handle error generation if there is an object conflict.
        actionexec_db = ActionExecution.add_or_update(actionexec_db)
        return ActionExecutionAPI.from_model(actionexec_db)

    @expose('json')
    def put(self, id, **kwargs):
        # TODO: Update probably does not make any sense on an execution.
        """
            Update a actionexecution.

            Handles requests:
                POST /actionexecutions/1?_method=put
                PUT /actionexecutions/1
        """
        return {"dummy": "put"}

    @wsme_pecan.wsexpose(None, wstypes.text)
    def delete(self, id):
        """
            Delete a actionexecution.

            Handles requests:
                POST /actionexecutions/1?_method=delete
                DELETE /actionexecutions/1
        """

        # TODO: Support delete by name
        # TODO: Delete should migrate the execution data to a history collection.

        actionexec = ActionExecution.get_by_id(id)
        ActionExecution.delete(actionexec)
