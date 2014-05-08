from pecan import expose
from pecan.rest import RestController


class StactionsController(RestController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of Stactions in the system.
    """

    # TODO: Investigate mako rendering
    #@expose('text_template.mako', content_type='text/plain')
    @expose('json')
    def get_one(self, id):
        """
            List staction by id.

            Handle:
                GET /stactions/1
        """
        return {"dummy": "value"}

    @expose('json')
    def get_all(self):
        """
            List all stactions.

            Handles requests:
                GET /stactions/
        """
        return {"dummy": "get_all"}

    @expose('json')
    def delete(self, id):
        """
            Delete a staction.

            Handles requests:
                POST /stactions/1?_method=delete
                DELETE /stactions/1
        """
        return {"dummy": "delete staction"}

    @expose('json')
    def post(self, **kwargs):
        """
            Create a new staction.

            Handles requests:
                POST /stactions/
        """
        print kwargs
        return {"dummy": "post"}
    
    @expose('json')
    def put(self, id, **kwargs):
        """
            Update a staction.

            Handles requests:
                POST /stactions/1?_method=delete
                DELETE /stactions/1
        """
        return {"dummy": "put"}
    
