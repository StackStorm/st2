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
from st2common.exceptions import StackStormBaseException
from st2common.rbac.types import GLOBAL_PERMISSION_TYPES

__all__ = [
    "AccessDeniedError",
    "ResourceTypeAccessDeniedError",
    "ResourceAccessDeniedError",
    "ResourceAccessDeniedPermissionIsolationError",
]


class AccessDeniedError(StackStormBaseException):
    """
    Class representing insufficient permission / access denied error.

    Also acts as a base class for all the access related errors.
    """

    def __init__(self, message, user_db):
        self.user_db = user_db
        super(AccessDeniedError, self).__init__(message)


class ResourceTypeAccessDeniedError(AccessDeniedError):
    """
    Class representing an error where user doesn't have a required permission.
    """

    def __init__(self, user_db, permission_type):
        self.permission_type = permission_type

        message = 'User "%s" doesn\'t have required permission "%s"' % (
            user_db.name,
            permission_type,
        )
        super(ResourceTypeAccessDeniedError, self).__init__(
            message=message, user_db=user_db
        )


class ResourceAccessDeniedError(AccessDeniedError):
    """
    Class representing an error where user doesn't have a required permission on a resource.
    """

    def __init__(self, user_db, resource_api_or_db, permission_type):
        self.resource_api_db = resource_api_or_db
        self.permission_type = permission_type

        resource_uid = resource_api_or_db.get_uid() if resource_api_or_db else "unknown"

        if resource_api_or_db and permission_type not in GLOBAL_PERMISSION_TYPES:
            message = (
                'User "%s" doesn\'t have required permission "%s" on resource "%s"'
                % (
                    user_db.name,
                    permission_type,
                    resource_uid,
                )
            )
        else:
            message = 'User "%s" doesn\'t have required permission "%s"' % (
                user_db.name,
                permission_type,
            )
        super(ResourceAccessDeniedError, self).__init__(
            message=message, user_db=user_db
        )


class ResourceAccessDeniedPermissionIsolationError(AccessDeniedError):
    """
    Class representing an error where user doesn't have a required permission on a resource due
    to resource permission isolation.
    """

    def __init__(self, user_db, resource_api_or_db, permission_type):
        self.resource_api_db = resource_api_or_db
        self.permission_type = permission_type

        resource_uid = resource_api_or_db.get_uid() if resource_api_or_db else "unknown"

        message = (
            'User "%s" doesn\'t have access to resource "%s" due to resource permission '
            "isolation." % (user_db.name, resource_uid)
        )
        super(ResourceAccessDeniedPermissionIsolationError, self).__init__(
            message=message, user_db=user_db
        )
