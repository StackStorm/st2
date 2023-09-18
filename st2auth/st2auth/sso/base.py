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

import abc
import six
from typing import List


__all__ = ["BaseSingleSignOnBackend", "BaseSingleSignOnBackendResponse"]


# This defines the expected response to be communicated back from verify_response methods
@six.add_metaclass(abc.ABCMeta)
class BaseSingleSignOnBackendResponse(object):
    username: str = None
    referer: str = None
    groups: List[str] = None

    def __init__(self, username=None, referer=None, groups=[]):
        self.username = username
        self.groups = groups
        self.referer = referer

    def __eq__(self, other):
        if other is None:
            return False
        return (
            self.username == other.username
            and self.groups == other.groups
            and self.referer == other.referer
        )

    def __repr__(self):
        return (
            f"BaseSingleSignOnBackendResponse(username={self.username}, groups={self.groups}"
            + f", referer={self.referer}"
        )


@six.add_metaclass(abc.ABCMeta)
class BaseSingleSignOnBackend(object):
    """
    Base single sign on authentication class.
    """

    def get_request_redirect_url(self, referer) -> str:
        msg = 'The function "get_request_redirect_url" is not implemented in the base SSO backend.'
        raise NotImplementedError(msg)

    def get_request_id_from_response(self, response) -> str:
        msg = (
            'The function "get_request_id_from_response" is not implemented'
            "in the base SSO backend."
        )
        raise NotImplementedError(msg)

    def verify_response(self, response) -> BaseSingleSignOnBackendResponse:
        msg = (
            'The function "verify_response" is not implemented in the base SSO backend.'
        )
        raise NotImplementedError(msg)
