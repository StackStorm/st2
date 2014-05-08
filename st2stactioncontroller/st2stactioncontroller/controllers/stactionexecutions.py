from pecan import expose
from pecan.rest import RestController


class StactionExecutionsController(RestController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of StactionExecutions in the system.
    """

    @expose('json')
    def get_one(self, id):
        """
            List stactionexecution by id.

            Handle:
                GET /stactionexecutions/1
        """
        return {"dummy": "execution_value"}

    @expose('json')
    def get_all(self):
        """ 
            List all stactionexecutions.

            Handles requests:
                GET /stactionexecutions/
        """
        return {"dummy": "get_all"}

    @expose('json')
    def delete(self, id):
        """ 
            Delete a stactionexecution.

            Handles requests:
                POST /stactionexecutions/1?_method=delete
                DELETE /stactionexecutions/1
        """
        # TODO: Delete should migrate the execution data to a history collection.
        return {"dummy": "delete stactionexecution"}

    @expose('json')
    def post(self, **kwargs):
        """ 
            Create a new stactionexecution.

            Handles requests:
                POST /stactionexecutions/
        """
        print kwargs
        return {"dummy": "post"}

    @expose('json')
    def put(self, id, **kwargs):
        # TODO: Update probably does not make any sense on an execution.
        """
            Update a stactionexecution.

            Handles requests:
                POST /stactionexecutions/1?_method=delete
                DELETE /stactionexecutions/1
        """
        return {"dummy": "put"}

