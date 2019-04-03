# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import codecs
import mimetypes

import six
from mongoengine import ValidationError

from st2api.controllers import resource
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common import log as logging
from st2common.content import utils
from st2common.models.api.action import ActionAPI
from st2common.models.utils import action_param_utils
from st2common.persistence.action import Action
from st2common.persistence.runner import RunnerType
from st2common.rbac.types import PermissionType
from st2common.rbac.backends import get_rbac_backend
from st2common.router import abort
from st2common.router import Response

__all__ = [
    'OverviewController',
    'ParametersViewController',
    'EntryPointController'
]

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


class ParametersViewController(object):

    def get_one(self, action_id, requester_user):
        return self._get_one(action_id, requester_user=requester_user)

    @staticmethod
    def _get_one(action_id, requester_user):
        """
            List merged action & runner parameters by action id.

            Handle:
                GET /actions/views/parameters/1
        """
        action_db = LookupUtils._get_action_by_id(action_id)

        permission_type = PermissionType.ACTION_VIEW
        rbac_utils = get_rbac_backend().get_utils_class()
        rbac_utils.assert_user_has_resource_db_permission(user_db=requester_user,
                                                          resource_db=action_db,
                                                          permission_type=permission_type)

        runner_db = LookupUtils._get_runner_by_name(action_db.runner_type['name'])
        all_params = action_param_utils.get_params_view(
            action_db=action_db, runner_db=runner_db, merged_only=True)

        return {'parameters': all_params}


class OverviewController(resource.ContentPackResourceController):
    model = ActionAPI
    access = Action
    supported_filters = {}

    query_options = {
        'sort': ['pack', 'name']
    }

    mandatory_include_fields_retrieve = [
        'pack',
        'name',
        'parameters',
        'runner_type'
    ]

    def get_one(self, ref_or_id, requester_user):
        """
            List action by id.

            Handle:
                GET /actions/views/overview/1
        """
        resp = super(OverviewController, self)._get_one(ref_or_id,
                                                        requester_user=requester_user,
                                                        permission_type=PermissionType.ACTION_VIEW)
        action_api = ActionAPI(**resp.json)
        result = self._transform_action_api(action_api=action_api, requester_user=requester_user)
        resp.json = result
        return resp

    def get_all(self, exclude_attributes=None, include_attributes=None, sort=None, offset=0,
                limit=None, requester_user=None, **raw_filters):
        """
            List all actions.

            Handles requests:
                GET /actions/views/overview
        """
        resp = super(OverviewController, self)._get_all(exclude_fields=exclude_attributes,
                                                        include_fields=include_attributes,
                                                        sort=sort,
                                                        offset=offset,
                                                        limit=limit,
                                                        raw_filters=raw_filters,
                                                        requester_user=requester_user)
        runner_type_names = set([])
        action_ids = []

        result = []
        for item in resp.json:
            action_api = ActionAPI(**item)
            result.append(action_api)

            runner_type_names.add(action_api.runner_type)
            action_ids.append(str(action_api.id))

        # Add combined runner and action parameters to the compound result object
        # NOTE: This approach results in 2 additional queries while previous one resulted in
        # N * 2 additional queries

        # 1. Retrieve all the respective runner objects - we only need parameters
        runner_type_dbs = RunnerType.query(name__in=runner_type_names,
                                           only_fields=['name', 'runner_parameters'])
        runner_type_dbs = dict([(runner_db.name, runner_db) for runner_db in runner_type_dbs])

        # 2. Retrieve all the respective action objects - we only need parameters
        action_dbs = dict([(action_db.id, action_db) for action_db in result])

        for action_api in result:
            action_db = action_dbs.get(action_api.id, None)
            runner_db = runner_type_dbs.get(action_api.runner_type, None)
            all_params = action_param_utils.get_params_view(action_db=action_db,
                                                            runner_db=runner_db,
                                                            merged_only=True)
            action_api.parameters = all_params

        resp.json = result
        return resp

    @staticmethod
    def _transform_action_api(action_api, requester_user):
        action_id = action_api.id
        result = ParametersViewController._get_one(action_id=action_id,
                                                   requester_user=requester_user)
        action_api.parameters = result.get('parameters', {})
        return action_api


class EntryPointController(resource.ContentPackResourceController):
    model = ActionAPI
    access = Action

    supported_filters = {}

    def get_all(self):
        return abort(404)

    def get_one(self, ref_or_id, requester_user):
        """
            Outputs the file associated with action entry_point

            Handles requests:
                GET /actions/views/entry_point/1
        """
        LOG.info('GET /actions/views/entry_point with ref_or_id=%s', ref_or_id)
        action_db = self._get_by_ref_or_id(ref_or_id=ref_or_id)

        permission_type = PermissionType.ACTION_VIEW
        rbac_utils = get_rbac_backend().get_utils_class()
        rbac_utils.assert_user_has_resource_db_permission(user_db=requester_user,
                                                          resource_db=action_db,
                                                          permission_type=permission_type)

        pack = getattr(action_db, 'pack', None)
        entry_point = getattr(action_db, 'entry_point', None)

        abs_path = utils.get_entry_point_abs_path(pack, entry_point)

        if not abs_path:
            raise StackStormDBObjectNotFoundError('Action ref_or_id=%s has no entry_point to output'
                                                  % ref_or_id)

        with codecs.open(abs_path, 'r') as fp:
            content = fp.read()

        # Ensure content is utf-8
        if isinstance(content, six.binary_type):
            content = content.decode('utf-8')

        try:
            content_type = mimetypes.guess_type(abs_path)[0]
        except Exception:
            content_type = None

        # Special case if /etc/mime.types doesn't contain entry for yaml, py
        if not content_type:
            _, extension = os.path.splitext(abs_path)
            if extension in ['.yaml', '.yml']:
                content_type = 'application/x-yaml'
            elif extension in ['.py']:
                content_type = 'application/x-python'
            else:
                content_type = 'text/plain'

        response = Response()
        response.headers['Content-Type'] = content_type
        response.text = content
        return response


class ActionViewsController(object):
    parameters = ParametersViewController()
    overview = OverviewController()
    entry_point = EntryPointController()


parameters_view_controller = ParametersViewController()
overview_controller = OverviewController()
entry_point_controller = EntryPointController()
