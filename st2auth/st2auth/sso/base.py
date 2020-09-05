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


__all__ = [
    'BaseSingleSignOnBackend'
]


@six.add_metaclass(abc.ABCMeta)
class BaseSingleSignOnBackend(object):
    """
    Base single sign on authentication class.
    """

    def get_request_redirect_url(self, referer):
        msg = 'The function "get_request_redirect_url" is not implemented in the base SSO backend.'
        raise NotImplementedError(msg)

    def verify_response(self, response):
        msg = 'The function "verify_response" is not implemented in the base SSO backend.'
        raise NotImplementedError(msg)
