import httplib
from pecan import expose
from pecan.rest import RestController

from wsme import types as wstypes
from wsmeext.pecan import wsexpose

from st2common.persistence.action import ActionExecution
from st2common.models.api.action import ActionExecutionAPI


class StactionExecutionsController(RestController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of ActionExecutions in the system.
    """

    @wsexpose(ActionExecutionAPI, wstypes.text)
    def get_one(self, id):
        """
            List actionexecution by id.

            Handle:
                GET /actionexecutions/1
        """
    
        actionexec_db = ActionExecution.get_by_id(id)

        # TODO: test/handle object not found.
        return ActionExectuionAPI.from_model(actionexec_db)


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

    @wsexpose(ActionExecutionAPI, body=ActionExecutionAPI)
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

    @wsexpose(None, wstypes.txt)
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
