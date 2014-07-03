import httplib
from pecan import abort
from pecan.rest import RestController

from wsme import types as wstypes
import wsmeext.pecan as wsme_pecan

from st2common import log as logging
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.models.api.actionrunner import ActionTypeAPI
from st2common.persistence.actionrunner import ActionType
from st2common.util.actionrunner_db import (get_actiontype_by_id, get_actiontype_by_name)

from st2actionrunner.container import get_runner_container


LOG = logging.getLogger(__name__)


ACTION_TYPES = {
                'internaldummy': {'name': 'internaldummy',
                                  'description': ('An internal action type for '
                                                  'development only.'),
                                  'enabled': True,
                                  'runner_parameter_names': ['command'],
                                  'runner_module': 'no.such.module',
                                  },
                'internaldummy-plugin': {'name': 'internaldummy-plugin',
                                     'description': ('An internal action type for '
                                              'development only. Implemented '
                                              'using a plugin.'),
                                     'enabled': True,
                                     'runner_parameter_names': ['command'],
                                     'runner_module': 'st2actionrunner.runners.internaldummy',
                                         },
                #'shellaction': {'name': 'shellaction',
                #                'description': 'A shell action type',
                #                'enabled': True,
                #                'runner_parameter_names': ['command'],
                #                'runner_module': 'test.runner',
                #                },
                #'sshaction': {'name': 'sshaction',
                #              'description': 'An ssh action type',
                #              'enabled': True,
                #              'runner_parameter_names': ['host', 'user', 'pwd', 'command'],
                #              'runner_module': 'test.sshrunner',
                #              },
                }


class ActionTypesController(RestController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of an ActionType in the system.
    """

    def _register_internal_actiontypes(self):
        LOG.debug('Registering actiontypes')
        for name in ACTION_TYPES:
            actiontype_db = None
            try:
                actiontype_db = get_actiontype_by_name(name)
            except StackStormDBObjectNotFoundError:
                LOG.debug('ActionType "%s" does not exist in DB', name)
            else:
                continue

            if actiontype_db is None:
                actiontype = ActionTypeAPI()
                fields = ACTION_TYPES[name]
                for (key, value) in fields.items():
                    LOG.debug('actiontype name=%s field=%s value=%s', name, key, value)
                    setattr(actiontype, key, value)

                actiontype_api = ActionTypeAPI.to_model(actiontype)
                LOG.debug('ActionType after field population: %s', actiontype_api)
                actiontype_db = ActionType.add_or_update(actiontype_api)
                LOG.debug('created actiontype name=%s in DB. Object: %s', name, actiontype_db)

        LOG.debug('Registering actiontypes complete')

    def __init__(self):
        self._register_internal_actiontypes()
        global runner_container
        runner_container = get_runner_container()

    @wsme_pecan.wsexpose(ActionTypeAPI, wstypes.text)
    def get_one(self, id):
        """
            List ActionType objects by id.

            Handle:
                GET /actiontypes/1
        """

        LOG.info('GET /actiontypes/ with id=%s', id)

        try:
            actiontype_db = get_actiontype_by_id(id)
        except StackStormDBObjectNotFoundError, e:
            LOG.error('GET /actiontypes/ with id="%s": %s', id, e.message)
            abort(httplib.NOT_FOUND)
        actiontype_api = ActionTypeAPI.from_model(actiontype_db)

        LOG.debug('GET /actiontypes/ with id=%s, client_result=%s', id, actiontype_api)
        return actiontype_api

    @wsme_pecan.wsexpose([ActionTypeAPI])
    def get_all(self):
        """
            List all ActionType objects.

            Handles requests:
                GET /actiontypes/
        """

        LOG.info('GET all /actiontypes/')

        actiontype_apis = [ActionTypeAPI.from_model(actiontype_db)
                           for actiontype_db in ActionType.get_all()]

        # TODO: Unpack list in log message
        LOG.debug('GET all /actiontypes/ client_result=%s', actiontype_apis)
        return actiontype_apis

    @wsme_pecan.wsexpose(ActionTypeAPI, body=ActionTypeAPI)
    def post(self, actiontype):
        """
            Update not supported for ActionType.

            Create a new ActionType object.

            Handles requests:
                POST /actiontypes/
        """

        abort(httplib.NOT_IMPLEMENTED)

    @wsme_pecan.wsexpose(ActionTypeAPI, body=ActionTypeAPI,
                         status_code=httplib.NOT_IMPLEMENTED)
    def put(self, action):
        """
            Update not supported for ActionType.

            Handles requests:
                POST /actiontypes/1?_method=put
                PUT /actiontypes/1
        """

        abort(httplib.METHOD_NOT_ALLOWED)

#    @wsme_pecan.wsexpose(None, wstypes.text,
#                         status_code=httplib.NOT_IMPLEMENTED)
#    def delete(self, id):
    @wsme_pecan.wsexpose(None,
                         status_code=httplib.NOT_IMPLEMENTED)
    def delete(self):
        """
            Delete an ActionType.

            Handles requests:
                POST /actiontypes/1?_method=delete
                DELETE /actiontypes/1
        """

        # TODO: Support delete by name
        abort(httplib.NOT_IMPLEMENTED)
