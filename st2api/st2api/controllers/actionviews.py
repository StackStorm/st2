from mongoengine import ValidationError
from pecan import abort
from pecan.rest import RestController
import six

import st2actions.utils.param_utils as param_utils
from st2actions.container.service import RunnerContainerService
from st2api.controllers import resource
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common import log as logging
from st2common.models.api.action import ActionAPI
from st2common.models.base import jsexpose
from st2common.persistence.action import (Action, RunnerType)

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)


class LookupUtils(object):

    @staticmethod
    def _get_action_by_id(id):
        try:
            return Action.get_by_id(id)
        except Exception as e:
            msg = 'Database lookup for id="%s" resulted in exception. %s' % (id, e)
            LOG.exception(msg)
            abort(http_client.NOT_FOUND, msg)

    @staticmethod
    def _get_runner_by_id(id):
        try:
            return RunnerType.get_by_id(id)
        except (ValueError, ValidationError) as e:
            msg = 'Database lookup for id="%s" resulted in exception. %s' % (id, e)
            LOG.exception(msg)
            abort(http_client.NOT_FOUND, msg)

    @staticmethod
    def _get_runner_by_name(name):
        try:
            return RunnerType.get_by_name(name)
        except (ValueError, ValidationError) as e:
            msg = 'Database lookup for name="%s" resulted in exception. %s' % (id, e)
            LOG.exception(msg)
            abort(http_client.NOT_FOUND, msg)


class ParametersViewController(RestController):

    @jsexpose(str, status_code=http_client.OK)
    def get_one(self, action_id):
        return self._get_one(action_id)

    @staticmethod
    def _get_one(action_id):
        """
            List merged action & runner parameters by action id.

            Handle:
                GET /actions/views/parameters/1
        """
        action_db = LookupUtils._get_action_by_id(action_id)
        LOG.info('Found action: %s, runner: %s', action_db, action_db.runner_type['name'])
        runner_db = LookupUtils._get_runner_by_name(action_db.runner_type['name'])

        all_params = param_utils.get_params_view(
            action_db=action_db, runner_db=runner_db, merged_only=True)

        return {'parameters': all_params}


class OverviewController(resource.ContentPackResourceControler):
    model = None
    access = None
    supported_filters = {}

    @jsexpose(str)
    def get_one(self, action_id):
        """
            List action by id.

            Handle:
                GET /actions/views/overview/1
        """

        LOG.info('GET /actions/views/overview with id=%s', action_id)
        action_db = LookupUtils._get_action_by_id(action_id)
        action_api = ActionAPI.from_model(action_db)
        return self._transform_action_api(action_api)

    @jsexpose(str)
    def get_all(self, **kwargs):
        """
            List all actions.

            Handles requests:
                GET /actions/views/overview
        """
        LOG.info('GET all /actions/views/overview with filters=%s', kwargs)
        kwargs = self._get_filters(**kwargs)
        action_dbs = Action.get_all(**kwargs)
        action_apis = [ActionAPI.from_model(action_db) for action_db in action_dbs]
        return map(self._transform_action_api, action_apis)

    def _transform_action_api(self, action_api):
        action_id = action_api.id
        action_api.parameters = ParametersViewController._get_one(action_id).get('parameters')
        del action_api.required_parameters
        return action_api


class EntryPointController(RestController):

    @jsexpose(str, content_type='text/plain', status_code=http_client.OK)
    def get_one(self, action_id):
        """
            Outputs the file associated with action entry_point

            Handles requests:
                GET /actions/views/entry_point/1
        """
        LOG.info('GET /actions/views/overview with id=%s', action_id)
        action_db = LookupUtils._get_action_by_id(action_id)

        pack = getattr(action_db, 'pack', None)
        entry_point = getattr(action_db, 'entry_point', None)

        abs_path = RunnerContainerService.get_entry_point_abs_path(pack, entry_point)

        if not abs_path:
            raise StackStormDBObjectNotFoundError('Action id=%s has no entry_point to output'
                                                  % action_id)

        with open(abs_path) as file:
            content = file.read()

        return content


class ActionViewsController(RestController):
    parameters = ParametersViewController()
    overview = OverviewController()
    entry_point = EntryPointController()
