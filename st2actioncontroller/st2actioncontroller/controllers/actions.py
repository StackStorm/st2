from pecan import expose
from pecan.rest import RestController

from wsme import types as wstypes
from wsmeext.pecan import wsexpose

from st2common.persistence.action import Action
from st2common.models.api.action import ActionAPI


class StactionsController(RestController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of Actions in the system.
    """

    # TODO: Investigate mako rendering
    #@expose('text_template.mako', content_type='text/plain')
#    @expose('json')
    @wsexpose(ActionAPI, wstypes.text)
    def get_one(self, id):
        """
            List action by id.

            Handle:
                GET /actions/1
        """

        action_db = Action.get_by_id(id)
        return ActionAPI.from_model(action_db)

    @expose('json')
    def get_all(self):
        """
            List all actions.

            Handles requests:
                GET /actions/
        """
        return {"dummy": "get_all"}

    @expose('json')
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
