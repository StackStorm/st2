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

import datetime

from st2common import log as logging
from st2common.persistence.auth import Token
from st2common.exceptions import auth as exceptions
from st2common.util import isotime

__all__ = [
    'validate_token'
]

LOG = logging.getLogger(__name__)


def validate_token(token_in_headers, token_in_query_params):
    """
    Validate the provided authentication token.

    :param token_in_headers: Authentication token provided via headers.
    :type token_in_headers: ``str``

    :param token_in_query_params: Authentication token provided via query params.
    :type token_in_query_params: ``str``

    :return: TokenDB object on success.
    :rtype: :class:`.TokenDB`
    """
    if not token_in_headers and not token_in_query_params:
        LOG.audit('Token is not found in header or query parameters.')
        raise exceptions.TokenNotProvidedError('Token is not provided.')

    if token_in_headers:
        LOG.audit('Token provided in headers')

    if token_in_query_params:
        LOG.audit('Token provided in query parameters')

    token_string = token_in_headers or token_in_query_params
    token = Token.get(token_string)

    if token.expiry <= isotime.add_utc_tz(datetime.datetime.utcnow()):
        # TODO: purge expired tokens
        LOG.audit('Token with id "%s" has expired.' % (token.id))
        raise exceptions.TokenExpiredError('Token has expired.')

    LOG.audit('Token with id "%s" is validated.' % (token.id))
    return token
