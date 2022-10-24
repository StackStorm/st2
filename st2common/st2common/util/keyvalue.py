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

from __future__ import absolute_import
import six
import logging

from oslo_config import cfg

from st2common.constants.keyvalue import ALL_SCOPE, DATASTORE_PARENT_SCOPE
from st2common.constants.keyvalue import DATASTORE_SCOPE_SEPARATOR
from st2common.constants.keyvalue import FULL_SYSTEM_SCOPE, FULL_USER_SCOPE
from st2common.constants.keyvalue import USER_SCOPE, ALLOWED_SCOPES
from st2common.exceptions.rbac import AccessDeniedError
from st2common.models.db.auth import UserDB
from st2common.persistence.keyvalue import KeyValuePair
from st2common.services.config import deserialize_key_value
from st2common.rbac.backends import get_rbac_backend
from st2common.rbac.types import PermissionType

__all__ = ["get_datastore_full_scope", "get_key"]

LOG = logging.getLogger(__name__)


def _validate_scope(scope):
    if scope not in ALLOWED_SCOPES:
        msg = "Scope %s is not in allowed scopes list: %s." % (scope, ALLOWED_SCOPES)
        raise ValueError(msg)


def _validate_decrypt_query_parameter(decrypt, scope, is_admin, user_db):
    """
    Validate that the provider user is either admin or requesting to decrypt value for
    themselves.
    """
    is_user_scope = scope == USER_SCOPE or scope == FULL_USER_SCOPE
    if decrypt and (not is_user_scope and not is_admin):
        msg = "Decrypt option requires administrator access"
        raise AccessDeniedError(message=msg, user_db=user_db)


def get_datastore_full_scope(scope):
    if scope == ALL_SCOPE:
        return scope

    if DATASTORE_PARENT_SCOPE in scope:
        return scope

    return "%s%s%s" % (DATASTORE_PARENT_SCOPE, DATASTORE_SCOPE_SEPARATOR, scope)


def _derive_scope_and_key(key, user, scope=None):
    """
    :param user: Name of the user.
    :type user: ``str``
    """
    if user and not isinstance(user, six.string_types):
        raise TypeError('"user" needs to be a string')

    if scope is not None:
        return scope, key

    if key.startswith("system."):
        return FULL_SYSTEM_SCOPE, key[key.index(".") + 1 :]

    return FULL_USER_SCOPE, "%s:%s" % (user, key)


def get_key(key=None, user_db=None, scope=None, decrypt=False):
    """
    Retrieve key from KVP store
    """
    if not isinstance(key, six.string_types):
        raise TypeError("Given key is not typeof string.")

    if not isinstance(decrypt, bool):
        raise TypeError("Decrypt parameter is not typeof bool.")

    if not user_db:
        # Use system user
        user_db = UserDB(name=cfg.CONF.system_user.user)

    scope, key_id = _derive_scope_and_key(key=key, user=user_db.name, scope=scope)
    scope = get_datastore_full_scope(scope)

    LOG.debug(
        "get_key key_id: %s, scope: %s, user: %s, decrypt: %s"
        % (key_id, scope, str(user_db.name), decrypt)
    )

    _validate_scope(scope=scope)

    # Get the key value pair by scope and name.
    kvp = KeyValuePair.get_by_scope_and_name(scope, key_id)

    # Check that user has permission to the key value pair.
    # If RBAC is enabled, this check will verify if user has system role with all access.
    # If RBAC is enabled, this check guards against a user accessing another user's kvp.
    # If RBAC is enabled, user needs to be explicitly granted permission to view a system kvp.
    # The check is sufficient to allow decryption of the system kvp.
    rbac_utils = get_rbac_backend().get_utils_class()
    rbac_utils.assert_user_has_resource_db_permission(
        user_db=user_db,
        resource_db=kvp,
        permission_type=PermissionType.KEY_VALUE_PAIR_VIEW,
    )

    # Decrypt in deserialize_key_value cannot handle NoneType.
    if kvp.value is None:
        return kvp.value

    return deserialize_key_value(kvp.value, decrypt)
