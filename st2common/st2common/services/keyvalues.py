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

from oslo_config import cfg

from st2common import log as logging

from st2common.constants.keyvalue import DATASTORE_PARENT_SCOPE
from st2common.constants.keyvalue import SYSTEM_SCOPE, FULL_SYSTEM_SCOPE
from st2common.constants.keyvalue import USER_SCOPE, FULL_USER_SCOPE
from st2common.constants.keyvalue import ALLOWED_SCOPES
from st2common.constants.keyvalue import DATASTORE_KEY_SEPARATOR, USER_SEPARATOR
from st2common.constants.types import ResourceType
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.exceptions.keyvalue import InvalidScopeException, InvalidUserException
from st2common.models.db.auth import UserDB
from st2common.models.system.keyvalue import UserKeyReference
from st2common.persistence.keyvalue import KeyValuePair
from st2common.persistence.rbac import UserRoleAssignment
from st2common.persistence.rbac import Role
from st2common.persistence.rbac import PermissionGrant
from st2common.rbac.backends import get_rbac_backend
from st2common.rbac.types import PermissionType

__all__ = [
    "get_kvp_for_name",
    "get_values_for_names",
    "KeyValueLookup",
    "UserKeyValueLookup",
]

LOG = logging.getLogger(__name__)


def get_kvp_for_name(name):
    try:
        kvp_db = KeyValuePair.get_by_name(name)
    except ValueError:
        kvp_db = None

    return kvp_db


def get_values_for_names(names, default_value=None):
    """
    Retrieve values for the provided key names (multi get).

    If a KeyValuePair objects for a particular name doesn't exist, the dictionary will contain
    default_value for that name.

    :rtype: ``dict``
    """
    result = {}
    kvp_dbs = KeyValuePair.get_by_names(names=names)

    name_to_kvp_db_map = {}
    for kvp_db in kvp_dbs:
        name_to_kvp_db_map[kvp_db.name] = kvp_db.value

    for name in names:
        result[name] = name_to_kvp_db_map.get(name, default_value)

    return result


class BaseKeyValueLookup(object):

    scope = None
    _key_prefix = None

    def get_key_name(self):
        """
        Function which returns an original key name.

        :rtype: ``str``
        """
        key_name_parts = [DATASTORE_PARENT_SCOPE, self.scope]
        key_name = self._key_prefix.split(":", 1)

        if len(key_name) == 1:
            key_name = key_name[0]
        elif len(key_name) >= 2:
            key_name = key_name[1]
        else:
            key_name = ""

        key_name_parts.append(key_name)
        key_name = ".".join(key_name_parts)
        return key_name


class KeyValueLookup(BaseKeyValueLookup):

    scope = SYSTEM_SCOPE

    def __init__(
        self,
        prefix=None,
        key_prefix=None,
        cache=None,
        scope=FULL_SYSTEM_SCOPE,
        context=None,
    ):
        if not scope:
            scope = FULL_SYSTEM_SCOPE

        if scope == SYSTEM_SCOPE:
            scope = FULL_SYSTEM_SCOPE

        self._prefix = prefix
        self._key_prefix = key_prefix or ""
        self._value_cache = cache or {}
        self._scope = scope

        self._context = context if context else dict()
        self._user = (
            context["user"]
            if context and "user" in context and context["user"]
            else cfg.CONF.system_user.user
        )
        self._user = (
            context["api_user"]
            if context and "api_user" in context and context["api_user"]
            else self._user
        )

    def __str__(self):
        return self._value_cache[self._key_prefix]

    def __int__(self):
        return int(float(self))

    def __float__(self):
        return float(str(self))

    def __getitem__(self, key):
        return self._get(key)

    def __getattr__(self, name):
        return self._get(name)

    def _get(self, name):
        # get the value for this key and save in value_cache
        if self._key_prefix:
            key = "%s.%s" % (self._key_prefix, name)
        else:
            key = name

        if self._prefix:
            kvp_key = DATASTORE_KEY_SEPARATOR.join([self._prefix, key])
        else:
            kvp_key = key

        value = self._get_kv(kvp_key)
        self._value_cache[key] = value
        # return a KeyValueLookup as response since the lookup may not be complete e.g. if
        # the lookup is for 'key_base.key_value' it is likely that the calling code, e.g. Jinja,
        # will expect to do a dictionary style lookup for key_base and key_value as subsequent
        # calls. Saving the value in cache avoids extra DB calls.
        return KeyValueLookup(
            prefix=self._prefix,
            key_prefix=key,
            cache=self._value_cache,
            scope=self._scope,
            context=self._context,
        )

    def _get_kv(self, key):
        scope = self._scope
        LOG.debug("Lookup system kv: scope: %s and key: %s", scope, key)

        try:
            kvp = KeyValuePair.get_by_scope_and_name(scope=scope, name=key)
        except StackStormDBObjectNotFoundError:
            kvp = None

        if kvp:
            LOG.debug("Got value %s from datastore.", kvp.value)

            # Check that user has permission to the key value pair.
            # If RBAC is enabled, this check will verify if user has system role with all access.
            # If RBAC is enabled, this check guards against a user accessing another user's kvp.
            # If RBAC is enabled, user needs to be explicitly granted permission to view a system kvp.
            # The check is sufficient to allow decryption of the system kvp.
            rbac_utils = get_rbac_backend().get_utils_class()
            rbac_utils.assert_user_has_resource_db_permission(
                user_db=UserDB(name=self._user),
                resource_db=kvp,
                permission_type=PermissionType.KEY_VALUE_PAIR_VIEW,
            )

        return kvp.value if kvp else ""


class UserKeyValueLookup(BaseKeyValueLookup):

    scope = USER_SCOPE

    def __init__(
        self,
        user,
        prefix=None,
        key_prefix=None,
        cache=None,
        scope=FULL_USER_SCOPE,
        context=None,
    ):
        if not scope:
            scope = FULL_USER_SCOPE

        if scope == USER_SCOPE:
            scope = FULL_USER_SCOPE

        self._prefix = prefix
        self._key_prefix = key_prefix or ""
        self._value_cache = cache or {}
        self._user = user
        self._scope = scope
        self._context = context if context else dict()

    def __str__(self):
        return self._value_cache[self._key_prefix]

    def __getitem__(self, key):
        return self._get(key)

    def __getattr__(self, name):
        return self._get(name)

    def _get(self, name):
        # get the value for this key and save in value_cache
        if self._key_prefix:
            key = "%s.%s" % (self._key_prefix, name)
        else:
            key = UserKeyReference(name=name, user=self._user).ref

        if self._prefix:
            kvp_key = DATASTORE_KEY_SEPARATOR.join([self._prefix, key])
        else:
            kvp_key = key

        value = self._get_kv(kvp_key)
        self._value_cache[key] = value
        # return a KeyValueLookup as response since the lookup may not be complete e.g. if
        # the lookup is for 'key_base.key_value' it is likely that the calling code, e.g. Jinja,
        # will expect to do a dictionary style lookup for key_base and key_value as subsequent
        # calls. Saving the value in cache avoids extra DB calls.
        return UserKeyValueLookup(
            prefix=self._prefix,
            user=self._user,
            key_prefix=key,
            cache=self._value_cache,
            scope=self._scope,
        )

    def _get_kv(self, key):
        scope = self._scope

        try:
            kvp = KeyValuePair.get_by_scope_and_name(scope=scope, name=key)
        except StackStormDBObjectNotFoundError:
            kvp = None

        return kvp.value if kvp else ""


def get_key_reference(scope, name, user=None):
    """
    Given a key name and user this method returns a new name (string ref)
    to address the key value pair in the context of that user.

    :param user: User to whom key belongs.
    :type user: ``str``

    :param name: Original name of the key.
    :type name: ``str``

    :rtype: ``str``
    """
    if scope == SYSTEM_SCOPE or scope == FULL_SYSTEM_SCOPE:
        return name
    elif scope == USER_SCOPE or scope == FULL_USER_SCOPE:
        if not user:
            raise InvalidUserException(
                "A valid user must be specified for user key ref."
            )
        return UserKeyReference(name=name, user=user).ref
    else:
        raise InvalidScopeException(
            'Scope "%s" is not valid. Allowed scopes are %s.' % (scope, ALLOWED_SCOPES)
        )


def get_key_uids_for_user(user):
    role_names = UserRoleAssignment.query(user=user).only("role").scalar("role")
    permission_grant_ids = Role.query(name__in=role_names).scalar("permission_grants")
    permission_grant_ids = sum(permission_grant_ids, [])
    permission_grants_filters = {}
    permission_grants_filters["id__in"] = permission_grant_ids
    permission_grants_filters["resource_type"] = ResourceType.KEY_VALUE_PAIR
    return PermissionGrant.query(**permission_grants_filters).scalar("resource_uid")


def get_all_system_kvp_names_for_user(user):
    """
    Retrieve all the permission grants for a particular user.
    The result will return the key list

    :rtype: ``list``
    """
    key_list = []

    for uid in get_key_uids_for_user(user):
        pfx = "%s%s%s" % (
            ResourceType.KEY_VALUE_PAIR,
            DATASTORE_KEY_SEPARATOR,
            FULL_SYSTEM_SCOPE,
        )
        if not uid.startswith(pfx):
            continue

        key_name = uid.split(DATASTORE_KEY_SEPARATOR)[2:]

        if key_name and key_name not in key_list:
            key_list.append(USER_SEPARATOR.join(key_name))

    return sorted(key_list)
