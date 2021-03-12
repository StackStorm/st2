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


class StackStormDBObjectNotFoundError(StackStormBaseException):
    pass


class StackStormDBObjectMalformedError(StackStormBaseException):
    pass


class StackStormDBObjectConflictError(StackStormBaseException):
    """
    Exception that captures a DB object conflict error.
    """

    def __init__(self, message, conflict_id, model_object):
        super(StackStormDBObjectConflictError, self).__init__(message)
        self.conflict_id = conflict_id
        self.model_object = model_object


class StackStormDBObjectWriteConflictError(StackStormBaseException):
    def __init__(self, instance):
        msg = 'Conflict saving DB object with id "%s" and rev "%s".' % (
            instance.id,
            instance.rev,
        )
        super(StackStormDBObjectWriteConflictError, self).__init__(msg)
