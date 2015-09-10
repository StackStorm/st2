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

import pecan
import six

from pecan import abort
from pecan.rest import RestController
from mongoengine import ValidationError

from st2common import log as logging
from st2common.models.api.auth import ApiKeyAPI
from st2common.models.api.base import jsexpose
from st2common.exceptions.auth import ApiKeyNotFoundError
from st2common.persistence.auth import ApiKey
from st2common.rbac.types import PermissionType
from st2common.rbac.decorators import request_user_has_permission
from st2common.rbac.decorators import request_user_has_resource_permission
from st2common.util import auth as auth_util

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)

__all__ = [
    'ApiKeyController'
]


class ApiKeyController(RestController):
    """
    Implements the REST endpoint for managing the key value store.
    """

    supported_filters = {
        'user': 'user'
    }

    query_options = {
        'sort': ['user']
    }

    def __init__(self):
        super(ApiKeyController, self).__init__()
        self.get_one_db_method = ApiKey.get_by_key_or_id

    @request_user_has_resource_permission(permission_type=PermissionType.API_KEY_VIEW)
    @jsexpose(arg_types=[str])
    def get_one(self, api_key_id_or_key):
        """
            List api keys.

            Handle:
                GET /apikeys/1
        """
        api_key_db = None
        try:
            api_key_db = ApiKey.get_by_key_or_id(api_key_id_or_key)
        except ApiKeyNotFoundError:
            msg = 'ApiKey matching %s for reference and id not found.', api_key_id_or_key
            LOG.exception(msg)
            abort(http_client.NOT_FOUND, msg)

        try:
            return ApiKeyAPI.from_model(api_key_db)
        except (ValidationError, ValueError) as e:
            LOG.exception('Failed to serialize API key.')
            abort(http_client.INTERNAL_SERVER_ERROR, str(e))

    @request_user_has_permission(permission_type=PermissionType.API_KEY_VIEW)
    @jsexpose(arg_types=[str])
    def get_all(self, **kw):
        """
            List all keys.

            Handles requests:
                GET /keys/
        """

        api_key_dbs = ApiKey.get_all(**kw)
        api_keys = [ApiKeyAPI.from_model(api_key_db) for api_key_db in api_key_dbs]

        return api_keys

    @request_user_has_permission(permission_type=PermissionType.API_KEY_CREATE)
    @jsexpose(body_cls=ApiKeyAPI, status_code=http_client.CREATED)
    def post(self, api_key):
        """
        Create a new entry or update an existing one.
        """
        api_key_db = None
        try:
            api_key.user = self._get_user(api_key)
            api_key.key = auth_util.generate_api_key()
            api_key_db = ApiKey.add_or_update(ApiKeyAPI.to_model(api_key))
        except (ValidationError, ValueError) as e:
            LOG.exception('Validation failed for api_key data=%s.', api_key)
            abort(http_client.BAD_REQUEST, str(e))

        extra = {'api_key_db': api_key_db}
        LOG.audit('ApiKey created. ApiKey.id=%s' % (api_key_db.id), extra=extra)

        api_key_api = ApiKeyAPI.from_model(api_key_db)
        return api_key_api

    @request_user_has_resource_permission(permission_type=PermissionType.API_KEY_DELETE)
    @jsexpose(arg_types=[str], status_code=http_client.NO_CONTENT)
    def delete(self, api_key_id_or_key):
        """
            Delete the key value pair.

            Handles requests:
                DELETE /apikeys/1
        """
        api_key_db = None
        try:
            api_key_db = ApiKey.get_by_key_or_id(api_key_id_or_key)
        except ApiKeyNotFoundError:
            msg = 'ApiKey matching %s for reference and id not found.', api_key_id_or_key
            LOG.exception(msg)
            abort(http_client.NOT_FOUND, msg)

        LOG.debug('DELETE /apikeys/ lookup with api_key_id_or_key=%s found object: %s',
                  api_key_id_or_key, api_key_db)

        try:
            ApiKey.delete(api_key_db)
        except Exception as e:
            LOG.exception('Database delete encountered exception during '
                          'delete of api_key_id_or_key="%s". ', api_key_id_or_key)
            abort(http_client.INTERNAL_SERVER_ERROR, str(e))
            return

        extra = {'api_key_db': api_key_db}
        LOG.audit('ApiKey deleted. ApiKey.id=%s' % (api_key_db.id), extra=extra)

    def _get_user(self, api_key):
        # If a user is provided in api_key try to use that value. In the future
        # this behavior should change.
        user = getattr(api_key, 'user', '')
        if user:
            return user

        # no user found in api_key lookup from request context.
        # AuthHook places context in the pecan request.
        auth_context = pecan.request.context.get('auth', None)

        if not auth_context:
            return None

        user_db = auth_context.get('user', None)
        return user_db.name if user_db else None
