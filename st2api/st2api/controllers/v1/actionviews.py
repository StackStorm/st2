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

from mongoengine import ValidationError
from pecan import abort
from pecan.rest import RestController
import six

from st2api.controllers import resource
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common import log as logging
from st2common.content import utils
from st2common.models.api.action import ActionAPI
from st2common.models.api.base import jsexpose
from st2common.models.utils import action_param_utils
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

    @jsexpose(arg_types=[str], status_code=http_client.OK)
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

    include_reference = True

    @jsexpose(arg_types=[str])
    def get_one(self, ref_or_id):
        """
            List action by id.

            Handle:
                GET /actions/views/overview/1
        """
        action_api = super(OverviewController, self)._get_one(ref_or_id)
        return self._transform_action_api(action_api)

    @jsexpose(arg_types=[str])
    def get_all(self, **kwargs):
        """
            List all actions.

            Handles requests:
                GET /actions/views/overview
        """
        action_apis = super(OverviewController, self)._get_all(**kwargs)
        return map(self._transform_action_api, action_apis)

    @staticmethod
    def _transform_action_api(action_api):
        action_id = action_api.id
        action_api.parameters = ParametersViewController._get_one(action_id).get('parameters')
        return action_api


class EntryPointController(resource.ContentPackResourceController):
    model = ActionAPI
    access = Action

    supported_filters = {}

    @jsexpose()
    def get_all(self, **kwargs):
        return abort(404)

    @jsexpose(arg_types=[str], content_type='text/plain', status_code=http_client.OK)
    def get_one(self, ref_or_id):
        """
            Outputs the file associated with action entry_point

            Handles requests:
                GET /actions/views/entry_point/1
        """
        LOG.info('GET /actions/views/overview with ref_or_id=%s', ref_or_id)
        action_db = self._get_by_ref_or_id(ref_or_id=ref_or_id)

        pack = getattr(action_db, 'pack', None)
        entry_point = getattr(action_db, 'entry_point', None)

        abs_path = utils.get_entry_point_abs_path(pack, entry_point)

        if not abs_path:
            raise StackStormDBObjectNotFoundError('Action ref_or_id=%s has no entry_point to output'
                                                  % ref_or_id)

        with open(abs_path) as file:
            content = file.read()

        return content


class ActionViewsController(RestController):
    parameters = ParametersViewController()
    overview = OverviewController()
    entry_point = EntryPointController()
