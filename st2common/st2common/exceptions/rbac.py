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

from st2common.exceptions import StackStormBaseException

__all__ = [
    'AccessDeniedError',
    'ResourceTypeAccessDeniedError',
    'ResourceAccessDeniedError'
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

        message = ('User "%s" doesn\t have required permission "%s"' % (user_db.name,
                                                                        permission_type))
        super(ResourceAccessDeniedError, self).__init__(message=message, user_db=user_db)

class ResourceAccessDeniedError(AccessDeniedError):
    """
    Class representing an error where user doesn't have a required permission on a resource.
    """

    def __init__(self, user_db, resource_db, permission_type):
        self.resource_db = resource_db
        self.permission_type = permission_type

        message = ('User "%s" doesn\t have required permission "%s" on resource "%s"' %
                   (user_db.name, resource_db.get_uid(), permission_type))
        super(ResourceAccessDeniedError, self).__init__(message=message, user_db=user_db)
