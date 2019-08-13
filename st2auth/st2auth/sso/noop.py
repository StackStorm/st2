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

from st2auth.sso.base import BaseSingleSignOnBackend


__all__ = [
    'NoOpSingleSignOnBackend'
]

NOT_IMPLEMENTED_MESSAGE = (
    'The default "noop" SSO backend is not a proper implementation. '
    'Please refer to the enterprise version for configuring SSO.'
)


class NoOpSingleSignOnBackend(BaseSingleSignOnBackend):
    """
    NoOp SSO authentication backend.
    """

    def get_request_redirect_url(self, referer):
        raise NotImplementedError(NOT_IMPLEMENTED_MESSAGE)

    def verify_response(self, response):
        raise NotImplementedError(NOT_IMPLEMENTED_MESSAGE)
