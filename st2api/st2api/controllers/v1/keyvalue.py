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
from pecan import abort
import six
from mongoengine import ValidationError

from st2api.controllers.resource import ResourceController
from st2common import log as logging
from st2common.constants.keyvalue import SYSTEM_SCOPE, USER_SCOPE, ALLOWED_SCOPES
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.exceptions.keyvalue import CryptoKeyNotSetupException, InvalidScopeException
from st2common.models.api.keyvalue import KeyValuePairAPI
from st2common.models.api.keyvalue import KeyValuePairSetAPI
from st2common.models.api.base import jsexpose
from st2common.persistence.keyvalue import KeyValuePair
from st2common.services import coordination
from st2common.services.keyvalues import get_key_reference
from st2common.util.api import get_requester
from st2common.exceptions.rbac import AccessDeniedError
from st2common.rbac.utils import request_user_is_admin
from st2common.rbac.utils import assert_request_user_is_admin_if_user_query_param_is_provider

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)

__all__ = [
    'KeyValuePairController'
]


class KeyValuePairController(ResourceController):
    """
    Implements the REST endpoint for managing the key value store.
    """

    model = KeyValuePairAPI
    access = KeyValuePair
    supported_filters = {
        'prefix': 'name__startswith',
        'scope': 'scope'
    }

    def __init__(self):
        super(KeyValuePairController, self).__init__()
        self._coordinator = coordination.get_coordinator()
        self.get_one_db_method = self._get_by_name

    @jsexpose(arg_types=[str, str, str, bool])
    def get_one(self, name, scope=SYSTEM_SCOPE, user=None, decrypt=False):
        """
            List key by name.

            Handle:
                GET /keys/key1
        """
        self._validate_scope(scope=scope)

        if user:
            # Providing a user implies a user scope
            scope = USER_SCOPE

        requester_user = get_requester()
        user = user or requester_user
        is_admin = request_user_is_admin(request=pecan.request)

        # User needs to be either admin or requesting item for itself
        self._validate_decrypt_query_parameter(decrypt=decrypt, scope=scope, is_admin=is_admin)

        # Validate that the authenticated user is admin if user query param is provided
        assert_request_user_is_admin_if_user_query_param_is_provider(request=pecan.request,
                                                                     user=user)

        key_ref = get_key_reference(scope=scope, name=name, user=user)
        from_model_kwargs = {'mask_secrets': not decrypt}
        kvp_api = self._get_one_by_scope_and_name(
            name=key_ref,
            scope=scope,
            from_model_kwargs=from_model_kwargs
        )

        return kvp_api

    @jsexpose(arg_types=[str, str, str, bool])
    def get_all(self, prefix=None, scope=SYSTEM_SCOPE, user=None, decrypt=False, **kwargs):
        """
            List all keys.

            Handles requests:
                GET /keys/
        """
        if user:
            # Providing a user implies a user scope
            scope = USER_SCOPE

        requester_user = get_requester()
        user = user or requester_user
        is_all_scope = (scope == 'all')
        is_admin = request_user_is_admin(request=pecan.request)

        if is_all_scope and not is_admin:
            msg = '"all" scope requires administrator access'
            raise AccessDeniedError(message=msg, user_db=requester_user)

        # User needs to be either admin or requesting items for themselves
        self._validate_decrypt_query_parameter(decrypt=decrypt, scope=scope, is_admin=is_admin)

        # Validate that the authenticated user is admin if user query param is provided
        assert_request_user_is_admin_if_user_query_param_is_provider(request=pecan.request,
                                                                     user=user)

        from_model_kwargs = {'mask_secrets': not decrypt}
        kwargs['prefix'] = prefix

        if scope and scope not in ['all']:
            self._validate_scope(scope=scope)
            kwargs['scope'] = scope

        if scope == USER_SCOPE:
            # Make sure we only returned values scoped to current user
            if kwargs['prefix']:
                kwargs['prefix'] = get_key_reference(name=kwargs['prefix'], scope=scope,
                                                     user=requester_user)
            else:
                kwargs['prefix'] = get_key_reference(name='', scope=scope,
                                                     user=user)

        kvp_apis = super(KeyValuePairController, self)._get_all(from_model_kwargs=from_model_kwargs,
                                                                **kwargs)
        return kvp_apis

    @jsexpose(arg_types=[str, str, str], body_cls=KeyValuePairSetAPI)
    def put(self, kvp, name, scope=SYSTEM_SCOPE):
        """
        Create a new entry or update an existing one.
        """
        self._validate_scope(scope=scope)

        requester_user = get_requester()

        scope = getattr(kvp, 'scope', scope)
        user = getattr(kvp, 'user', requester_user) or requester_user

        # Validate that the authenticated user is admin if user query param is provided
        assert_request_user_is_admin_if_user_query_param_is_provider(request=pecan.request,
                                                                     user=user)

        key_ref = get_key_reference(scope=scope, name=name, user=user)
        lock_name = self._get_lock_name_for_key(name=key_ref, scope=scope)
        LOG.debug('PUT scope: %s, name: %s', scope, name)
        # TODO: Custom permission check since the key doesn't need to exist here

        # Note: We use lock to avoid a race
        with self._coordinator.get_lock(lock_name):
            try:
                existing_kvp_api = self._get_one_by_scope_and_name(
                    scope=scope,
                    name=key_ref
                )
            except StackStormDBObjectNotFoundError:
                existing_kvp_api = None

            kvp.name = key_ref
            kvp.scope = scope

            try:
                kvp_db = KeyValuePairAPI.to_model(kvp)

                if existing_kvp_api:
                    kvp_db.id = existing_kvp_api.id

                kvp_db = KeyValuePair.add_or_update(kvp_db)
            except (ValidationError, ValueError) as e:
                LOG.exception('Validation failed for key value data=%s', kvp)
                abort(http_client.BAD_REQUEST, str(e))
                return
            except CryptoKeyNotSetupException as e:
                LOG.exception(str(e))
                abort(http_client.BAD_REQUEST, str(e))
                return
            except InvalidScopeException as e:
                LOG.exception(str(e))
                abort(http_client.BAD_REQUEST, str(e))
                return
        extra = {'kvp_db': kvp_db}
        LOG.audit('KeyValuePair updated. KeyValuePair.id=%s' % (kvp_db.id), extra=extra)

        kvp_api = KeyValuePairAPI.from_model(kvp_db)
        return kvp_api

    @jsexpose(arg_types=[str, str, str], status_code=http_client.NO_CONTENT)
    def delete(self, name, scope=SYSTEM_SCOPE, user=None):
        """
            Delete the key value pair.

            Handles requests:
                DELETE /keys/1
        """
        self._validate_scope(scope=scope)

        requester_user = get_requester()
        user = user or requester_user

        # Validate that the authenticated user is admin if user query param is provided
        assert_request_user_is_admin_if_user_query_param_is_provider(request=pecan.request,
                                                                     user=user)

        key_ref = get_key_reference(scope=scope, name=name, user=user)
        lock_name = self._get_lock_name_for_key(name=key_ref, scope=scope)

        # Note: We use lock to avoid a race
        with self._coordinator.get_lock(lock_name):
            from_model_kwargs = {'mask_secrets': True}
            kvp_api = self._get_one_by_scope_and_name(
                name=key_ref,
                scope=scope,
                from_model_kwargs=from_model_kwargs
            )

            kvp_db = KeyValuePairAPI.to_model(kvp_api)

            LOG.debug('DELETE /keys/ lookup with scope=%s name=%s found object: %s',
                      scope, name, kvp_db)

            try:
                KeyValuePair.delete(kvp_db)
            except Exception as e:
                LOG.exception('Database delete encountered exception during '
                              'delete of name="%s". ', name)
                abort(http_client.INTERNAL_SERVER_ERROR, str(e))
                return

        extra = {'kvp_db': kvp_db}
        LOG.audit('KeyValuePair deleted. KeyValuePair.id=%s' % (kvp_db.id), extra=extra)

    def _get_lock_name_for_key(self, name, scope=SYSTEM_SCOPE):
        """
        Retrieve a coordination lock name for the provided datastore item name.

        :param name: Datastore item name (PK).
        :type name: ``str``
        """
        lock_name = 'kvp-crud-%s.%s' % (scope, name)
        return lock_name

    def _validate_decrypt_query_parameter(self, decrypt, scope, is_admin):
        """
        Validate that the provider user is either admin or requesting to decrypt value for
        themselves.
        """
        requester_user = get_requester()

        if decrypt and (scope != USER_SCOPE and not is_admin):
            msg = 'Decrypt option requires administrator access'
            raise AccessDeniedError(message=msg, user_db=requester_user)

    def _validate_scope(self, scope):
        if scope not in ALLOWED_SCOPES:
            msg = 'Scope %s is not in allowed scopes list: %s.' % (scope, ALLOWED_SCOPES)
            raise ValueError(msg)
