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

from __future__ import absolute_import
from st2common.exceptions import StackStormBaseException
from st2common.exceptions.db import StackStormDBObjectNotFoundError

__all__ = [
    'TokenNotProvidedError',
    'TokenNotFoundError',
    'TokenExpiredError',
    'TTLTooLargeException',
    'ApiKeyNotProvidedError',
    'ApiKeyNotFoundError',
    'MultipleAuthSourcesError',
    'NoAuthSourceProvidedError',
    'NoNicknameOriginProvidedError',
    'UserNotFoundError',
    'AmbiguousUserError',
    'NotServiceUserError'
]


class TokenNotProvidedError(StackStormBaseException):
    pass


class TokenNotFoundError(StackStormDBObjectNotFoundError):
    pass


class TokenExpiredError(StackStormBaseException):
    pass


class TTLTooLargeException(StackStormBaseException):
    pass


class ApiKeyNotProvidedError(StackStormBaseException):
    pass


class ApiKeyNotFoundError(StackStormDBObjectNotFoundError):
    pass


class ApiKeyDisabledError(StackStormDBObjectNotFoundError):
    pass


class MultipleAuthSourcesError(StackStormBaseException):
    pass


class NoAuthSourceProvidedError(StackStormBaseException):
    pass


class NoNicknameOriginProvidedError(StackStormBaseException):
    pass


class UserNotFoundError(StackStormBaseException):
    pass


class AmbiguousUserError(StackStormBaseException):
    pass


class NotServiceUserError(StackStormBaseException):
    pass
