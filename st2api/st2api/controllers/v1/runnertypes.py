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

import six
from mongoengine import ValidationError

from st2common import log as logging
from st2common.models.api.action import RunnerTypeAPI
from st2common.persistence.runner import RunnerType
from st2api.controllers.resource import ResourceController
from st2common.rbac.types import PermissionType
from st2common.rbac.backends import get_rbac_backend
from st2common.router import abort

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)


class RunnerTypesController(ResourceController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of an RunnerType in the system.
    """

    model = RunnerTypeAPI
    access = RunnerType
    supported_filters = {
        'name': 'name'
    }

    query_options = {
        'sort': ['name']
    }

    def get_all(self, exclude_attributes=None, include_attributes=None, sort=None, offset=0,
                limit=None, requester_user=None, **raw_filters):
        return super(RunnerTypesController, self)._get_all(exclude_fields=exclude_attributes,
                                                           include_fields=include_attributes,
                                                           sort=sort,
                                                           offset=offset,
                                                           limit=limit,
                                                           raw_filters=raw_filters,
                                                           requester_user=requester_user)

    def get_one(self, name_or_id, requester_user):
        return self._get_one_by_name_or_id(name_or_id,
                                           requester_user=requester_user,
                                           permission_type=PermissionType.RUNNER_VIEW)

    def put(self, runner_type_api, name_or_id, requester_user):
        # Note: We only allow "enabled" attribute of the runner to be changed
        runner_type_db = self._get_by_name_or_id(name_or_id=name_or_id)

        permission_type = PermissionType.RUNNER_MODIFY
        rbac_utils = get_rbac_backend().get_utils_class()
        rbac_utils.assert_user_has_resource_db_permission(user_db=requester_user,
                                                          resource_db=runner_type_db,
                                                          permission_type=permission_type)

        old_runner_type_db = runner_type_db
        LOG.debug('PUT /runnertypes/ lookup with id=%s found object: %s', name_or_id,
                  runner_type_db)

        try:
            if runner_type_api.id and runner_type_api.id != name_or_id:
                LOG.warning('Discarding mismatched id=%s found in payload and using uri_id=%s.',
                            runner_type_api.id, name_or_id)

            runner_type_db.enabled = runner_type_api.enabled
            runner_type_db = RunnerType.add_or_update(runner_type_db)
        except (ValidationError, ValueError) as e:
            LOG.exception('Validation failed for runner type data=%s', runner_type_api)
            abort(http_client.BAD_REQUEST, six.text_type(e))
            return

        extra = {'old_runner_type_db': old_runner_type_db, 'new_runner_type_db': runner_type_db}
        LOG.audit('Runner Type updated. RunnerType.id=%s.' % (runner_type_db.id), extra=extra)
        runner_type_api = RunnerTypeAPI.from_model(runner_type_db)
        return runner_type_api


runner_types_controller = RunnerTypesController()
