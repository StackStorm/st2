from pecan import expose
from pecan.rest import RestController


class StactionExecutionsController(RestController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of ActionExecutions in the system.
    """

    @expose('json')
    def get_one(self, id):
        """
            List actionexecution by id.

            Handle:
                GET /actionexecutions/1
        """
        return {"dummy": "execution_value"}

    @expose('json')
    def get_all(self):
        """ 
            List all actionexecutions.

            Handles requests:
                GET /actionexecutions/
        """
        return {"dummy": "get_all"}

    @expose('json')
    def post(self, **kwargs):
        """ 
            Create a new actionexecution.

            Handles requests:
                POST /actionexecutions/
        """
        print kwargs
        return {"dummy": "post"}

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

    @expose('json')
    def delete(self, id):
        """ 
            Delete a actionexecution.

            Handles requests:
                POST /actionexecutions/1?_method=delete
                DELETE /actionexecutions/1
        """
        # TODO: Delete should migrate the execution data to a history collection.
        return {"dummy": "delete actionexecution"}
