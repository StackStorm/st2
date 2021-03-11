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

from st2common import exceptions as st2_exc
from st2common import log as logging


LOG = logging.getLogger(__name__)


class InvalidInquiryInstance(st2_exc.StackStormBaseException):
    def __init__(self, inquiry_id):
        Exception.__init__(
            self, 'Action execution "%s" is not an inquiry.' % inquiry_id
        )


class InquiryTimedOut(st2_exc.StackStormBaseException):
    def __init__(self, inquiry_id):
        Exception.__init__(
            self, 'Inquiry "%s" timed out and cannot be responded to.' % inquiry_id
        )


class InquiryAlreadyResponded(st2_exc.StackStormBaseException):
    def __init__(self, inquiry_id):
        Exception.__init__(
            self, 'Inquiry "%s" has already been responded to.' % inquiry_id
        )


class InquiryResponseUnauthorized(st2_exc.StackStormBaseException):
    def __init__(self, inquiry_id, user):
        msg = 'User "%s" does not have permission to respond to inquiry "%s".'
        Exception.__init__(self, msg % (user, inquiry_id))


class InvalidInquiryResponse(st2_exc.StackStormBaseException):
    def __init__(self, inquiry_id, error):
        msg = 'Response for inquiry "%s" did not pass schema validation. %s'
        Exception.__init__(self, msg % (inquiry_id, error))
