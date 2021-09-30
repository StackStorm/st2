# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
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
from st2common.exceptions.keyvalue import (
    CryptoKeyNotSetupException,
    InvalidScopeException,
)
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
from st2common.rbac.types import PermissionType
from st2common.models.db.keyvalue import KeyValuePairDB
from st2common.services.keyvalues import get_all_system_kvp_names_for_user

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)

__all__ = ["KeyValuePairController"]


class KeyValuePairController(ResourceController):
    """
    Implements the REST endpoint for managing the key value store.
    """

    model = KeyValuePairAPI
    access = KeyValuePair
    supported_filters = {"prefix": "name__startswith", "scope": "scope"}

    def __init__(self):
        super(KeyValuePairController, self).__init__()
        self._coordinator = coordination.get_coordinator()
        self.get_one_db_method = self._get_by_name

    def get_one(self, name, requester_user, scope=None, user=None, decrypt=False):
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
            requester_user = UserDB(name=cfg.CONF.system_user.user)

        scope = get_datastore_full_scope(scope)
        self._validate_scope(scope=scope)

        # User needs to be either admin or requesting item for itself
        self._validate_decrypt_query_parameter(
            decrypt=decrypt, scope=scope, requester_user=requester_user
        )

        user_query_param_filter = bool(user)
        current_user = requester_user.name
        user = user or requester_user.name

        rbac_utils = get_rbac_backend().get_utils_class()

        # Validate that the authenticated user is admin if user query param is provided
        rbac_utils.assert_user_is_admin_if_user_query_param_is_provided(
            user_db=requester_user, user=user, require_rbac=True
        )

        # Additional guard to ensure there is no information leakage across users
        is_admin = rbac_utils.user_is_admin(user_db=requester_user)

        if is_admin and user_query_param_filter:
            if scope == USER_SCOPE:
                raise ValueError("Invalid scope: %s" % (scope))
            else:
                # Retrieve values scoped to the provided user
                user_scope_prefix = get_key_reference(name=name, scope=scope, user=user)
        else:
            # RBAC not enabled or user is not an admin, retrieve user scoped values for the
            # current user
            user_scope_prefix = get_key_reference(
                name=name, scope=USER_SCOPE, user=current_user
            )

        if scope == FULL_USER_SCOPE:
            key_ref = user_scope_prefix
        elif scope == FULL_SYSTEM_SCOPE:
            key_ref = get_key_reference(scope=FULL_SYSTEM_SCOPE, name=name, user=user)
        else:
            raise ValueError("Invalid scope: %s" % (scope))

        if (user and scope == FULL_SYSTEM_SCOPE) or (scope == FULL_SYSTEM_SCOPE):
            permission_type = PermissionType.KEY_VALUE_PAIR_VIEW
            rbac_utils.assert_user_has_resource_db_permission(
                user_db=requester_user,
                resource_db=KeyValuePairDB(scope=scope, name=key_ref),
                permission_type=permission_type,
            )

        from_model_kwargs = {"mask_secrets": not decrypt}
        kvp_api = self._get_one_by_scope_and_name(
            name=key_ref, scope=scope, from_model_kwargs=from_model_kwargs
        )

        return kvp_api

    def get_all(
        self,
        requester_user,
        prefix=None,
        scope=None,
        user=None,
        decrypt=False,
        sort=None,
        offset=0,
        limit=None,
        **raw_filters,
    ):
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
            requester_user = UserDB(name=cfg.CONF.system_user.user)

        scope = get_datastore_full_scope(scope)

        if scope not in [ALL_SCOPE] + ALLOWED_SCOPES:
            raise ValueError("Invalid scope: %s" % (scope))

        # User needs to be either admin or requesting items for themselves
        self._validate_decrypt_query_parameter(
            decrypt=decrypt, scope=scope, requester_user=requester_user
        )

        user_query_param_filter = bool(user)

        current_user = requester_user.name
        user = user or requester_user.name

        rbac_utils = get_rbac_backend().get_utils_class()

        # Validate that the authenticated user is admin if user query param is provided
        rbac_utils.assert_user_is_admin_if_user_query_param_is_provided(
            user_db=requester_user, user=user, require_rbac=True
        )

        from_model_kwargs = {"mask_secrets": not decrypt}

        if scope and scope not in ALL_SCOPE:
            self._validate_scope(scope=scope)
            raw_filters["scope"] = scope

        # Set prefix which will be used for user-scoped items.
        # NOTE: It's very important raw_filters['prefix'] is set when requesting user scoped items
        # to avoid information leakage (aka user1 retrieves items for user2)
        is_admin = rbac_utils.user_is_admin(user_db=requester_user)

        # Check that an admin user has permission to all system scoped items.
        if is_admin and scope in [ALL_SCOPE, SYSTEM_SCOPE, FULL_SYSTEM_SCOPE]:
            rbac_utils.assert_user_has_resource_db_permission(
                user_db=requester_user,
                resource_db=KeyValuePairDB(scope=FULL_SYSTEM_SCOPE),
                permission_type=PermissionType.KEY_VALUE_PAIR_LIST,
            )

        if is_admin and user_query_param_filter:
            # Check that the user has permission to the user scoped items.
            rbac_utils.assert_user_has_resource_db_permission(
                user_db=requester_user,
                resource_db=KeyValuePairDB(scope="%s:%s" % (FULL_USER_SCOPE, user)),
                permission_type=PermissionType.KEY_VALUE_PAIR_LIST,
            )

            # Retrieve values scoped to the provided user
            user_scope_prefix = get_key_reference(
                name=prefix or "", scope=FULL_USER_SCOPE, user=user
            )
        else:
            # Check that the user has permission to the his/her own user scoped items.
            rbac_utils.assert_user_has_resource_db_permission(
                user_db=requester_user,
                resource_db=KeyValuePairDB(scope="%s:%s" % (FULL_USER_SCOPE, current_user)),
                permission_type=PermissionType.KEY_VALUE_PAIR_LIST,
            )

            # RBAC not enabled or user is not an admin, retrieve user scoped items
            # for the current user.
            user_scope_prefix = get_key_reference(
                name=prefix or "", scope=FULL_USER_SCOPE, user=current_user
            )

        # Special cases for ALL_SCOPE
        # 1. If user is an admin, then retrieves all system scoped items else only
        #    specific system scoped items that the user is granted permission to.
        # 2. Retrieves all the user scoped items that the current user owns.
        kvp_apis_system = []
        kvp_apis_user = []

        if scope in [ALL_SCOPE, SYSTEM_SCOPE, FULL_SYSTEM_SCOPE]:
            # If user is an admin, then retrieve all system scoped items
            if is_admin:
                raw_filters["scope"] = FULL_SYSTEM_SCOPE
                raw_filters["prefix"] = prefix

                items = self._get_all(
                    from_model_kwargs=from_model_kwargs,
                    sort=sort,
                    offset=offset,
                    limit=limit,
                    raw_filters=raw_filters,
                    requester_user=requester_user,
                )

                kvp_apis_system.extend(items.json or [])
            else:
                # Otherwise if user is not an admin, then get the list of
                # system scoped items that user is granted permission to.
                for key in get_all_system_kvp_names_for_user(current_user):
                    try:
                        item = self._get_one_by_scope_and_name(
                            from_model_kwargs=from_model_kwargs,
                            scope=FULL_SYSTEM_SCOPE,
                            name=key,
                        )

                        kvp_apis_system.append(item)
                    except Exception as e:
                        LOG.error("Unable to get key %s: %s", key, str(e))

        if scope in [ALL_SCOPE, USER_SCOPE, FULL_USER_SCOPE]:
            # Retrieves all the user scoped items that the current user owns.
            raw_filters["scope"] = FULL_USER_SCOPE
            raw_filters["prefix"] = user_scope_prefix

            items = self._get_all(
                from_model_kwargs=from_model_kwargs,
                sort=sort,
                offset=offset,
                limit=limit,
                raw_filters=raw_filters,
                requester_user=requester_user,
            )

            kvp_apis_user.extend(items.json)

        return kvp_apis_system + kvp_apis_user

    def put(self, kvp, name, requester_user, scope=None):
        """
        Create a new entry or update an existing one.
        """
        if not scope:
            scope = FULL_SYSTEM_SCOPE

        if not requester_user:
            requester_user = UserDB(name=cfg.CONF.system_user.user)

        scope = getattr(kvp, "scope", scope)
        scope = get_datastore_full_scope(scope)
        self._validate_scope(scope=scope)

        user = getattr(kvp, "user", requester_user.name) or requester_user.name

        # Validate that the authenticated user is admin if user query param is provided
        rbac_utils = get_rbac_backend().get_utils_class()
        rbac_utils.assert_user_is_admin_if_user_query_param_is_provided(
            user_db=requester_user, user=user, require_rbac=True
        )

        # Validate that encrypted option can only be used by admins
        encrypted = getattr(kvp, "encrypted", False)
        self._validate_encrypted_query_parameter(
            encrypted=encrypted, scope=scope, requester_user=requester_user
        )

        key_ref = get_key_reference(scope=scope, name=name, user=user)
        lock_name = self._get_lock_name_for_key(name=key_ref, scope=scope)
        LOG.debug("PUT scope: %s, name: %s", scope, name)

        if (user and scope == FULL_SYSTEM_SCOPE) or (scope == FULL_SYSTEM_SCOPE):
            permission_type = PermissionType.KEY_VALUE_PAIR_SET
            rbac_utils.assert_user_has_resource_db_permission(
                user_db=requester_user,
                resource_db=KeyValuePairDB(scope=scope, name=key_ref),
                permission_type=permission_type,
            )

        # TODO: Custom permission check since the key doesn't need to exist here

        # Note: We use lock to avoid a race
        with self._coordinator.get_lock(lock_name):
            try:
                existing_kvp_api = self._get_one_by_scope_and_name(
                    scope=scope, name=key_ref
                )
            except StackStormDBObjectNotFoundError:
                existing_kvp_api = None

            # st2client sends invalid id when initially setting a key so we ignore those
            id_ = kvp.__dict__.get("id", None)
            if not existing_kvp_api and id_ and not bson.ObjectId.is_valid(id_):
                del kvp.__dict__["id"]

            kvp.name = key_ref
            kvp.scope = scope

            try:
                kvp_db = KeyValuePairAPI.to_model(kvp)

                if existing_kvp_api:
                    kvp_db.id = existing_kvp_api.id

                kvp_db = KeyValuePair.add_or_update(kvp_db)
            except (ValidationError, ValueError) as e:
                LOG.exception("Validation failed for key value data=%s", kvp)
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
        extra = {"kvp_db": kvp_db}
        LOG.audit("KeyValuePair updated. KeyValuePair.id=%s" % (kvp_db.id), extra=extra)

        kvp_api = KeyValuePairAPI.from_model(kvp_db)
        return kvp_api

    def delete(self, name, requester_user, scope=None, user=None):
        """
        Delete the key value pair.

        Handles requests:
            DELETE /keys/1
        """
        if not scope:
            scope = FULL_SYSTEM_SCOPE

        if not requester_user:
            requester_user = UserDB(name=cfg.CONF.system_user.user)

        scope = get_datastore_full_scope(scope)
        self._validate_scope(scope=scope)

        user = user or requester_user.name

        # Validate that the authenticated user is admin if user query param is provided
        rbac_utils = get_rbac_backend().get_utils_class()
        rbac_utils.assert_user_is_admin_if_user_query_param_is_provided(
            user_db=requester_user, user=user, require_rbac=True
        )

        key_ref = get_key_reference(scope=scope, name=name, user=user)
        lock_name = self._get_lock_name_for_key(name=key_ref, scope=scope)

        if (user and scope == FULL_SYSTEM_SCOPE) or (scope == FULL_SYSTEM_SCOPE):
            permission_type = PermissionType.KEY_VALUE_PAIR_DELETE
            rbac_utils.assert_user_has_resource_db_permission(
                user_db=requester_user,
                resource_db=KeyValuePairDB(scope=scope, name=key_ref),
                permission_type=permission_type,
            )

        # Note: We use lock to avoid a race
        with self._coordinator.get_lock(lock_name):
            from_model_kwargs = {"mask_secrets": True}
            kvp_api = self._get_one_by_scope_and_name(
                name=key_ref, scope=scope, from_model_kwargs=from_model_kwargs
            )

            kvp_db = KeyValuePairAPI.to_model(kvp_api)

            LOG.debug(
                "DELETE /keys/ lookup with scope=%s name=%s found object: %s",
                scope,
                name,
                kvp_db,
            )

            try:
                KeyValuePair.delete(kvp_db)
            except Exception as e:
                LOG.exception(
                    "Database delete encountered exception during "
                    'delete of name="%s". ',
                    name,
                )
                abort(http_client.INTERNAL_SERVER_ERROR, six.text_type(e))
                return

        extra = {"kvp_db": kvp_db}
        LOG.audit("KeyValuePair deleted. KeyValuePair.id=%s" % (kvp_db.id), extra=extra)

        return Response(status=http_client.NO_CONTENT)

    def _get_lock_name_for_key(self, name, scope=FULL_SYSTEM_SCOPE):
        """
        Retrieve a coordination lock name for the provided datastore item name.

        :param name: Datastore item name (PK).
        :type name: ``str``
        """
        lock_name = six.b("kvp-crud-%s.%s" % (scope, name))
        return lock_name

    def _validate_decrypt_query_parameter(self, decrypt, scope, requester_user):
        """
        Validate that the provider user is either admin or requesting to decrypt value for
        themselves.
        """
        rbac_utils = get_rbac_backend().get_utils_class()
        is_admin = rbac_utils.user_is_admin(user_db=requester_user)
        is_user_scope = scope == USER_SCOPE or scope == FULL_USER_SCOPE

        if decrypt and (not is_user_scope and not is_admin):
            msg = "Decrypt option requires administrator access"
            raise AccessDeniedError(message=msg, user_db=requester_user)

    def _validate_encrypted_query_parameter(self, encrypted, scope, requester_user):
        rbac_utils = get_rbac_backend().get_utils_class()
        is_admin = rbac_utils.user_is_admin(user_db=requester_user)
        if encrypted and not is_admin:
            msg = "Pre-encrypted option requires administrator access"
            raise AccessDeniedError(message=msg, user_db=requester_user)

    def _validate_scope(self, scope):
        if scope not in ALLOWED_SCOPES:
            msg = "Scope %s is not in allowed scopes list: %s." % (
                scope,
                ALLOWED_SCOPES,
            )
            raise ValueError(msg)


key_value_pair_controller = KeyValuePairController()
