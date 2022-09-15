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
from st2common.rbac.types import PermissionType, ResourceType
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
        if not scope or scope == ALL_SCOPE:
            # Default to system scope
            scope = FULL_SYSTEM_SCOPE

        if user:
            # Providing a user implies a user scope
            scope = FULL_USER_SCOPE

        if not requester_user:
            requester_user = UserDB(name=cfg.CONF.system_user.user)

        scope = get_datastore_full_scope(scope)
        self._validate_scope(scope=scope)

        user = user or requester_user.name

        rbac_utils = get_rbac_backend().get_utils_class()

        # Validate that the authenticated user is admin if user query param is provided
        rbac_utils.assert_user_is_admin_if_user_query_param_is_provided(
            user_db=requester_user, user=user, require_rbac=True
        )

        # Set key reference for system or user scope
        key_ref = get_key_reference(scope=scope, name=name, user=user)
        extra = {"scope": scope, "name": name, "user": user, "key_ref": key_ref}
        LOG.debug("GET /v1/keys/%s", name, extra=extra)

        # Setup a kvp database object used for verifying permission
        kvp_db = KeyValuePairDB(
            uid="%s:%s:%s" % (ResourceType.KEY_VALUE_PAIR, scope, key_ref),
            scope=scope,
            name=key_ref,
        )

        # Check that user has permission to the key value pair.
        # If RBAC is enabled, this check will verify if user has system role with all access.
        # If RBAC is enabled, this check guards against a user accessing another user's kvp.
        # If RBAC is enabled, user needs to be explicitly granted permission to view a system kvp.
        # The check is sufficient to allow decryption of the system kvp.
        rbac_utils.assert_user_has_resource_db_permission(
            user_db=requester_user,
            resource_db=kvp_db,
            permission_type=PermissionType.KEY_VALUE_PAIR_VIEW,
        )

        from_model_kwargs = {"mask_secrets": not decrypt}
        kvp_api = self._get_one_by_scope_and_name(
            name=key_ref, scope=scope, from_model_kwargs=from_model_kwargs
        )
        if decrypt and kvp_api.secret:
            LOG.audit(
                "User %s decrypted the value %s ",
                user,
                name,
                extra={
                    "user": user,
                    "scope": scope,
                    "key_name": name,
                    "operation": "decrypt",
                },
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

        # Check if user is granted one of the system roles.
        has_system_role = rbac_utils.user_has_system_role(user_db=requester_user)

        # Check that an admin user has permission to all system scoped items.
        if has_system_role and scope in [ALL_SCOPE, SYSTEM_SCOPE, FULL_SYSTEM_SCOPE]:
            rbac_utils.assert_user_has_resource_db_permission(
                user_db=requester_user,
                resource_db=KeyValuePairDB(scope=FULL_SYSTEM_SCOPE),
                permission_type=PermissionType.KEY_VALUE_PAIR_LIST,
            )

        # Check that user has permission to user scoped items for provided user or current user.
        if user and scope in [ALL_SCOPE, USER_SCOPE, FULL_USER_SCOPE]:
            rbac_utils.assert_user_has_resource_db_permission(
                user_db=requester_user,
                resource_db=KeyValuePairDB(scope="%s:%s" % (FULL_USER_SCOPE, user)),
                permission_type=PermissionType.KEY_VALUE_PAIR_LIST,
            )

        # Set user scope prefix for the provided user (or current user if user not provided)
        # NOTE: It's very important raw_filters['prefix'] is set when requesting user scoped
        # items to avoid information leakage (aka user1 retrieves items for user2)
        name_for_keyref = ""
        if "name" in raw_filters and raw_filters["name"]:
            name_for_keyref = raw_filters["name"]
        else:
            name_for_keyref = prefix or ""

        user_scope_prefix = get_key_reference(
            name=name_for_keyref, scope=FULL_USER_SCOPE, user=user
        )

        # Special cases for ALL_SCOPE
        # 1. If user is an admin, then retrieves all system scoped items else only
        #    specific system scoped items that the user is granted permission to.
        # 2. Retrieves all the user scoped items that the current user owns.
        kvp_apis_system = []
        kvp_apis_user = []

        if scope in [ALL_SCOPE, SYSTEM_SCOPE, FULL_SYSTEM_SCOPE]:
            decrypted_keys = []
            # If user has system role, then retrieve all system scoped items
            if has_system_role:
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
                if decrypt and items.json:
                    decrypted_keys.extend(
                        kv_api["name"] for kv_api in items.json if kv_api["secret"]
                    )
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
                        continue
                    if decrypt and item.secret:
                        decrypted_keys.append(key)
            if decrypted_keys:
                LOG.audit(
                    "User %s decrypted the values %s ",
                    user,
                    decrypted_keys,
                    extra={
                        "User": user,
                        "scope": FULL_SYSTEM_SCOPE,
                        "key_name": decrypted_keys,
                        "operation": "decrypt",
                    },
                )

        if scope in [ALL_SCOPE, USER_SCOPE, FULL_USER_SCOPE]:
            # Retrieves all the user scoped items that the current user owns.
            raw_filters["scope"] = FULL_USER_SCOPE
            if "name" in raw_filters and raw_filters["name"]:
                raw_filters["name"] = user_scope_prefix
            else:
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
            if decrypt and items.json:
                decrypted_keys = [
                    kvp_api["name"] for kvp_api in items.json if kvp_api["secret"]
                ]
                if decrypted_keys:
                    LOG.audit(
                        "User %s decrypted the values %s ",
                        user,
                        decrypted_keys,
                        extra={
                            "User": user,
                            "scope": FULL_USER_SCOPE,
                            "key_name": decrypted_keys,
                            "operation": "decrypt",
                        },
                    )

        return kvp_apis_system + kvp_apis_user

    def put(self, kvp, name, requester_user, scope=None):
        """
        Create a new entry or update an existing one.
        """
        if not scope or scope == ALL_SCOPE:
            # Default to system scope
            scope = FULL_SYSTEM_SCOPE

        if not requester_user:
            requester_user = UserDB(name=cfg.CONF.system_user.user)

        scope = getattr(kvp, "scope", scope)
        scope = get_datastore_full_scope(scope)
        self._validate_scope(scope=scope)

        user = getattr(kvp, "user", requester_user.name) or requester_user.name

        rbac_utils = get_rbac_backend().get_utils_class()

        # Validate that the authenticated user is admin if user query param is provided
        rbac_utils.assert_user_is_admin_if_user_query_param_is_provided(
            user_db=requester_user, user=user, require_rbac=True
        )

        # Set key reference for system or user scope
        key_ref = get_key_reference(scope=scope, name=name, user=user)
        extra = {"scope": scope, "name": name, "user": user, "key_ref": key_ref}
        LOG.debug("PUT /v1/keys/%s", name, extra=extra)

        # Setup a kvp database object used for verifying permission
        kvp_db = KeyValuePairDB(
            uid="%s:%s:%s" % (ResourceType.KEY_VALUE_PAIR, scope, key_ref),
            scope=scope,
            name=key_ref,
        )

        # Check that user has permission to the key value pair.
        # If RBAC is enabled, this check will verify if user has system role with all access.
        # If RBAC is enabled, this check guards against a user accessing another user's kvp.
        # If RBAC is enabled, user needs to be explicitly granted permission to set a system kvp.
        # The check is sufficient to allow decryption of the system kvp.
        rbac_utils.assert_user_has_resource_db_permission(
            user_db=requester_user,
            resource_db=kvp_db,
            permission_type=PermissionType.KEY_VALUE_PAIR_SET,
        )

        # Validate that the pre-encrypted option can only be used by admins
        encrypted = getattr(kvp, "encrypted", False)
        self._validate_encrypted_query_parameter(
            encrypted=encrypted, scope=scope, requester_user=requester_user
        )

        # Acquire a lock to avoid race condition between concurrent API calls
        with self._coordinator.get_lock(
            self._get_lock_name_for_key(name=key_ref, scope=scope)
        ):
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

        extra["kvp_db"] = kvp_db
        LOG.audit("PUT /v1/keys/%s succeeded id=%s", name, kvp_db.id, extra=extra)

        return KeyValuePairAPI.from_model(kvp_db)

    def delete(self, name, requester_user, scope=None, user=None):
        """
        Delete the key value pair.

        Handles requests:
            DELETE /keys/1
        """
        if not scope or scope == ALL_SCOPE:
            # Default to system scope
            scope = FULL_SYSTEM_SCOPE

        if not requester_user:
            requester_user = UserDB(name=cfg.CONF.system_user.user)

        scope = get_datastore_full_scope(scope)
        self._validate_scope(scope=scope)

        user = user or requester_user.name

        rbac_utils = get_rbac_backend().get_utils_class()

        # Validate that the authenticated user is admin if user query param is provided
        rbac_utils.assert_user_is_admin_if_user_query_param_is_provided(
            user_db=requester_user, user=user, require_rbac=True
        )

        # Set key reference for system or user scope
        key_ref = get_key_reference(scope=scope, name=name, user=user)
        extra = {"scope": scope, "name": name, "user": user, "key_ref": key_ref}
        LOG.debug("DELETE /v1/keys/%s", name, extra=extra)

        # Setup a kvp database object used for verifying permission
        kvp_db = KeyValuePairDB(
            uid="%s:%s:%s" % (ResourceType.KEY_VALUE_PAIR, scope, key_ref),
            scope=scope,
            name=key_ref,
        )

        # Check that user has permission to the key value pair.
        # If RBAC is enabled, this check will verify if user has system role with all access.
        # If RBAC is enabled, this check guards against a user accessing another user's kvp.
        # If RBAC is enabled, user needs to be explicitly granted permission to delete a system kvp.
        # The check is sufficient to allow decryption of the system kvp.
        rbac_utils.assert_user_has_resource_db_permission(
            user_db=requester_user,
            resource_db=kvp_db,
            permission_type=PermissionType.KEY_VALUE_PAIR_DELETE,
        )

        # Acquire a lock to avoid race condition between concurrent API calls
        with self._coordinator.get_lock(
            self._get_lock_name_for_key(name=key_ref, scope=scope)
        ):
            from_model_kwargs = {"mask_secrets": True}
            kvp_api = self._get_one_by_scope_and_name(
                name=key_ref, scope=scope, from_model_kwargs=from_model_kwargs
            )
            kvp_db = KeyValuePairAPI.to_model(kvp_api)

            extra["kvp_db"] = kvp_db
            LOG.debug("DELETE /v1/keys/%s", name, extra=extra)

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

        LOG.audit("DELETE /v1/keys/%s succeeded id=%s", name, kvp_db.id, extra=extra)

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
