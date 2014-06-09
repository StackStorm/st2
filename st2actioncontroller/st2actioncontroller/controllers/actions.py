import httplib
import logging
from pecan import expose
from pecan.rest import RestController

from wsme import types as wstypes
from wsmeext.pecan import wsexpose

from st2common.persistence.action import Action
from st2common.models.api.action import ActionAPI


LOG = logging.getLogger('st2actioncontroller')


class StactionsController(RestController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of Actions in the system.
    """

    # TODO: Investigate mako rendering
    # @expose('text_template.mako', content_type='text/plain')
    @wsexpose(ActionAPI, wstypes.text)
    def get_one(self, id):
        """
            List action by id.

            Handle:
                GET /actions/1
        """

        action_db = Action.get_by_id(id)

        # TODO: test/handle object not found.
        return ActionAPI.from_model(action_db)

    # TODO: Update to wsexpose
    @expose('json')
    def get_all(self, **kwargs):
        """
            List all actions.

            Handles requests:
                GET /actions/
        """

        if not kwargs:
            actions = ActionAPI()
            actions.actions = [ActionAPI.from_model(action_db)
                               for action_db in Action.get_all()]
            return actions
        else:
            # TODO: implement id=foo and name=foo lookup to support query semantics.
            return {"dummy": "get_all", "kwargs": str(kwargs)}

    @wsexpose(ActionAPI, body=ActionAPI, status_code=httplib.CREATED)
    def post(self, action):
        """
            Create a new action.

            Handles requests:
                POST /actions/
        """

        action_db = ActionAPI.to_model(action)
        # TODO: POST operations should only add to DB.
        #       If an existing object conflicts then raise error.
        action_db = Action.add_or_update(action_db)
        return ActionAPI.from_model(action_db)

    @expose('json')
    def put(self, id, **kwargs):
        """
            Update an action.

            Handles requests:
                POST /actions/1?_method=put
                PUT /actions/1
        """
        # TODO: Implement
        return {"dummy": "put"}

    @wsexpose(None, wstypes.text)
    def delete(self, id):
        """
            Delete an action.

            Handles requests:
                POST /actions/1?_method=delete
                DELETE /actions/1
        """

        # TODO: Support delete by name
        action = Action.get_by_id(id)
        # TODO: Implement no-such object error handling

        Action.delete(action)
