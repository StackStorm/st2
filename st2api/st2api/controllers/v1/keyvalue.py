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

from oslo_config import cfg

import six
import bson
from mongoengine import ValidationError

from st2api.controllers.resource import ResourceController
from st2common import log as logging
from st2common.constants.keyvalue import ALL_SCOPE, FULL_SYSTEM_SCOPE, SYSTEM_SCOPE
from st2common.constants.keyvalue import FULL_USER_SCOPE, USER_SCOPE, ALLOWED_SCOPES
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.exceptions.keyvalue import CryptoKeyNotSetupException, InvalidScopeException
from st2common.models.api.keyvalue import KeyValuePairAPI
from st2common.models.db.auth import UserDB
from st2common.persistence.keyvalue import KeyValuePair
from st2common.services import coordination
from st2common.services.keyvalues import get_key_reference
from st2common.util.keyvalue import get_datastore_full_scope
from st2common.exceptions.rbac import AccessDeniedError
from st2common.rbac.backends import get_rbac_backend
from st2common.router import abort
from st2common.router import Response

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

    def get_one(self, name, requester_user, scope=FULL_SYSTEM_SCOPE, user=None, decrypt=False):
        """
            List key by name.

            Handle:
                GET /keys/key1
        """
        if not scope:
            # Default to system scope
            scope = FULL_SYSTEM_SCOPE

        if user:
            # Providing a user implies a user scope
            scope = FULL_USER_SCOPE

        if not requester_user:
            requester_user = UserDB(cfg.CONF.system_user.user)

        scope = get_datastore_full_scope(scope)
        self._validate_scope(scope=scope)

        # User needs to be either admin or requesting item for itself
        self._validate_decrypt_query_parameter(decrypt=decrypt, scope=scope,
                                               requester_user=requester_user)

        user_query_param_filter = bool(user)

        current_user = requester_user.name
        user = user or requester_user.name

        rbac_utils = get_rbac_backend().get_utils_class()

        # Validate that the authenticated user is admin if user query param is provided
        rbac_utils.assert_user_is_admin_if_user_query_param_is_provided(user_db=requester_user,
                                                                        user=user,
                                                                        require_rbac=True)

        # Additional guard to ensure there is no information leakage across users
        is_admin = rbac_utils.user_is_admin(user_db=requester_user)

        if is_admin and user_query_param_filter:
            # Retrieve values scoped to the provided user
            user_scope_prefix = get_key_reference(name=name, scope=USER_SCOPE, user=user)
        else:
            # RBAC not enabled or user is not an admin, retrieve user scoped values for the
            # current user
            user_scope_prefix = get_key_reference(name=name, scope=USER_SCOPE,
                                                  user=current_user)

        if scope == FULL_USER_SCOPE:
            key_ref = user_scope_prefix
        elif scope == FULL_SYSTEM_SCOPE:
            key_ref = get_key_reference(scope=FULL_SYSTEM_SCOPE, name=name, user=user)
        else:
            raise ValueError('Invalid scope: %s' % (scope))

        from_model_kwargs = {'mask_secrets': not decrypt}
        kvp_api = self._get_one_by_scope_and_name(
            name=key_ref,
            scope=scope,
            from_model_kwargs=from_model_kwargs
        )

        return kvp_api

    def get_all(self, requester_user, prefix=None, scope=FULL_SYSTEM_SCOPE, user=None,
                decrypt=False, sort=None, offset=0, limit=None, **raw_filters):
        """
            List all keys.

            Handles requests:
                GET /keys/
        """
        if not scope:
            # Default to system scope
            scope = FULL_SYSTEM_SCOPE

        if user:
            # Providing a user implies a user scope
            scope = FULL_USER_SCOPE

        if not requester_user:
            requester_user = UserDB(cfg.CONF.system_user.user)

        scope = get_datastore_full_scope(scope)

        # "all" scope can only be used by the admins (on RBAC installations)
        self._validate_all_scope(scope=scope, requester_user=requester_user)

        # User needs to be either admin or requesting items for themselves
        self._validate_decrypt_query_parameter(decrypt=decrypt, scope=scope,
                                               requester_user=requester_user)

        user_query_param_filter = bool(user)

        current_user = requester_user.name
        user = user or requester_user.name

        rbac_utils = get_rbac_backend().get_utils_class()

        # Validate that the authenticated user is admin if user query param is provided
        rbac_utils.assert_user_is_admin_if_user_query_param_is_provided(user_db=requester_user,
                                                                        user=user,
                                                                        require_rbac=True)

        from_model_kwargs = {'mask_secrets': not decrypt}

        if scope and scope not in ALL_SCOPE:
            self._validate_scope(scope=scope)
            raw_filters['scope'] = scope

        # Set prefix which will be used for user-scoped items.
        # NOTE: It's very important raw_filters['prefix'] is set when requesting user scoped items
        # to avoid information leakage (aka user1 retrieves items for user2)
        is_admin = rbac_utils.user_is_admin(user_db=requester_user)

        if is_admin and user_query_param_filter:
            # Retrieve values scoped to the provided user
            user_scope_prefix = get_key_reference(name=prefix or '', scope=USER_SCOPE, user=user)
        else:
            # RBAC not enabled or user is not an admin, retrieve user scoped values for the
            # current user
            user_scope_prefix = get_key_reference(name=prefix or '', scope=USER_SCOPE,
                                                  user=current_user)

        if scope == ALL_SCOPE:
            # Special case for ALL_SCOPE
            # 1. Retrieve system scoped values
            raw_filters['scope'] = FULL_SYSTEM_SCOPE
            raw_filters['prefix'] = prefix

            assert 'scope' in raw_filters
            kvp_apis_system = super(KeyValuePairController, self)._get_all(
                from_model_kwargs=from_model_kwargs,
                sort=sort,
                offset=offset,
                limit=limit,
                raw_filters=raw_filters,
                requester_user=requester_user)

            # 2. Retrieve user scoped items for current user or for all the users (depending if the
            # authenticated user is admin and if ?user is provided)
            raw_filters['scope'] = FULL_USER_SCOPE

            if cfg.CONF.rbac.enable and is_admin and not user_query_param_filter:
                # Admin user retrieving user-scoped items for all the users
                raw_filters['prefix'] = prefix or ''
            else:
                raw_filters['prefix'] = user_scope_prefix

            assert 'scope' in raw_filters
            assert 'prefix' in raw_filters
            kvp_apis_user = super(KeyValuePairController, self)._get_all(
                from_model_kwargs=from_model_kwargs,
                sort=sort,
                offset=offset,
                limit=limit,
                raw_filters=raw_filters,
                requester_user=requester_user)

            # Combine the result
            kvp_apis = []
            kvp_apis.extend(kvp_apis_system.json or [])
            kvp_apis.extend(kvp_apis_user.json or [])
        elif scope in [USER_SCOPE, FULL_USER_SCOPE]:
            # Make sure we only returned values scoped to current user
            prefix = get_key_reference(name=prefix or '', scope=scope, user=user)
            raw_filters['prefix'] = user_scope_prefix

            assert 'scope' in raw_filters
            assert 'prefix' in raw_filters
            kvp_apis = super(KeyValuePairController, self)._get_all(
                from_model_kwargs=from_model_kwargs,
                sort=sort,
                offset=offset,
                limit=limit,
                raw_filters=raw_filters,
                requester_user=requester_user)
        elif scope in [SYSTEM_SCOPE, FULL_SYSTEM_SCOPE]:
            raw_filters['prefix'] = prefix

            assert 'scope' in raw_filters
            kvp_apis = super(KeyValuePairController, self)._get_all(
                from_model_kwargs=from_model_kwargs,
                sort=sort,
                offset=offset,
                limit=limit,
                raw_filters=raw_filters,
                requester_user=requester_user)
        else:
            raise ValueError('Invalid scope: %s' % (scope))

        return kvp_apis

    def put(self, kvp, name, requester_user, scope=FULL_SYSTEM_SCOPE):
        """
        Create a new entry or update an existing one.
        """
        if not scope:
            scope = FULL_SYSTEM_SCOPE

        if not requester_user:
            requester_user = UserDB(cfg.CONF.system_user.user)

        scope = getattr(kvp, 'scope', scope)
        scope = get_datastore_full_scope(scope)
        self._validate_scope(scope=scope)

        user = getattr(kvp, 'user', requester_user.name) or requester_user.name

        # Validate that the authenticated user is admin if user query param is provided
        rbac_utils = get_rbac_backend().get_utils_class()
        rbac_utils.assert_user_is_admin_if_user_query_param_is_provided(user_db=requester_user,
                                                                        user=user,
                                                                        require_rbac=True)

        # Validate that encrypted option can only be used by admins
        encrypted = getattr(kvp, 'encrypted', False)
        self._validate_encrypted_query_parameter(encrypted=encrypted, scope=scope,
                                                 requester_user=requester_user)

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

            # st2client sends invalid id when initially setting a key so we ignore those
            id_ = kvp.__dict__.get('id', None)
            if not existing_kvp_api and id_ and not bson.ObjectId.is_valid(id_):
                del kvp.__dict__['id']

            kvp.name = key_ref
            kvp.scope = scope

            try:
                kvp_db = KeyValuePairAPI.to_model(kvp)

                if existing_kvp_api:
                    kvp_db.id = existing_kvp_api.id

                kvp_db = KeyValuePair.add_or_update(kvp_db)
            except (ValidationError, ValueError) as e:
                LOG.exception('Validation failed for key value data=%s', kvp)
                abort(http_client.BAD_REQUEST, six.text_type(e))
                return
            except CryptoKeyNotSetupException as e:
                LOG.exception(six.text_type(e))
                abort(http_client.BAD_REQUEST, six.text_type(e))
                return
            except InvalidScopeException as e:
                LOG.exception(six.text_type(e))
                abort(http_client.BAD_REQUEST, six.text_type(e))
                return
        extra = {'kvp_db': kvp_db}
        LOG.audit('KeyValuePair updated. KeyValuePair.id=%s' % (kvp_db.id), extra=extra)

        kvp_api = KeyValuePairAPI.from_model(kvp_db)
        return kvp_api

    def delete(self, name, requester_user, scope=FULL_SYSTEM_SCOPE, user=None):
        """
            Delete the key value pair.

            Handles requests:
                DELETE /keys/1
        """
        if not scope:
            scope = FULL_SYSTEM_SCOPE

        if not requester_user:
            requester_user = UserDB(cfg.CONF.system_user.user)

        scope = get_datastore_full_scope(scope)
        self._validate_scope(scope=scope)

        user = user or requester_user.name

        # Validate that the authenticated user is admin if user query param is provided
        rbac_utils = get_rbac_backend().get_utils_class()
        rbac_utils.assert_user_is_admin_if_user_query_param_is_provided(user_db=requester_user,
                                                                        user=user,
                                                                        require_rbac=True)

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
                abort(http_client.INTERNAL_SERVER_ERROR, six.text_type(e))
                return

        extra = {'kvp_db': kvp_db}
        LOG.audit('KeyValuePair deleted. KeyValuePair.id=%s' % (kvp_db.id), extra=extra)

        return Response(status=http_client.NO_CONTENT)

    def _get_lock_name_for_key(self, name, scope=FULL_SYSTEM_SCOPE):
        """
        Retrieve a coordination lock name for the provided datastore item name.

        :param name: Datastore item name (PK).
        :type name: ``str``
        """
        lock_name = six.b('kvp-crud-%s.%s' % (scope, name))
        return lock_name

    def _validate_all_scope(self, scope, requester_user):
        """
        Validate that "all" scope can only be provided by admins on RBAC installations.
        """
        scope = get_datastore_full_scope(scope)
        is_all_scope = (scope == ALL_SCOPE)
        rbac_utils = get_rbac_backend().get_utils_class()
        is_admin = rbac_utils.user_is_admin(user_db=requester_user)

        if is_all_scope and not is_admin:
            msg = '"all" scope requires administrator access'
            raise AccessDeniedError(message=msg, user_db=requester_user)

    def _validate_decrypt_query_parameter(self, decrypt, scope, requester_user):
        """
        Validate that the provider user is either admin or requesting to decrypt value for
        themselves.
        """
        rbac_utils = get_rbac_backend().get_utils_class()
        is_admin = rbac_utils.user_is_admin(user_db=requester_user)
        is_user_scope = (scope == USER_SCOPE or scope == FULL_USER_SCOPE)

        if decrypt and (not is_user_scope and not is_admin):
            msg = 'Decrypt option requires administrator access'
            raise AccessDeniedError(message=msg, user_db=requester_user)

    def _validate_encrypted_query_parameter(self, encrypted, scope, requester_user):
        rbac_utils = get_rbac_backend().get_utils_class()
        is_admin = rbac_utils.user_is_admin(user_db=requester_user)
        if encrypted and not is_admin:
            msg = 'Pre-encrypted option requires administrator access'
            raise AccessDeniedError(message=msg, user_db=requester_user)

    def _validate_scope(self, scope):
        if scope not in ALLOWED_SCOPES:
            msg = 'Scope %s is not in allowed scopes list: %s.' % (scope, ALLOWED_SCOPES)
            raise ValueError(msg)


key_value_pair_controller = KeyValuePairController()
