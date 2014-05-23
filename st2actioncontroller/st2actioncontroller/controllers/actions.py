from pecan import expose
from pecan.rest import RestController
from wsmeext.pecan import wsexpose

#from st2common.models.db import action as actionDB

#from st2common.models.db import action as actionDB
from st2common.models.api import action as actionAPImodel


class StactionsController(RestController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of Actions in the system.
    """

    # TODO: Investigate mako rendering
    #@expose('text_template.mako', content_type='text/plain')
#    @expose('json')
    @wsexpose(actionAPImodel.ActionAPI, body=actionAPImodel.ActionAPI)
    def get_one(self, id):
        """
            List action by id.

            Handle:
                GET /actions/1
        """
        return {"dummy": "value", "id": id}

    @expose('json')
    def get_all(self):
        """
            List all actions.

            Handles requests:
                GET /actions/
        """
        return {"dummy": "get_all"}

    #@expose('json')
    @wsexpose(actionAPImodel.ActionAPI, body=actionAPImodel.ActionAPI)
    def post(self, **kwargs):
        """
            Create a new action.

            Handles requests:
                POST /actions/
        """
        print kwargs
        return {"dummy": "post", "id": id}
    
    @expose('json')
    def put(self, id, **kwargs):
        """
            Update a action.

            Handles requests:
                POST /actions/1?_method=put
                PUT /actions/1
        """
        return {"dummy": "put"}

    @expose('json')
    def delete(self, id):
        """
            Delete a action.

            Handles requests:
                POST /actions/1?_method=delete
                DELETE /actions/1
        """
        return {"dummy": "delete action"}
