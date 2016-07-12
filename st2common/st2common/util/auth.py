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

import base64
import hashlib
import os
import random

from st2common import log as logging
from st2common.persistence.auth import Token, ApiKey
from st2common.exceptions import auth as exceptions
from st2common.util import date as date_utils
from st2common.util import hash as hash_utils

__all__ = [
    'validate_token',
    'validate_token_and_source',
    'generate_api_key',
    'validate_api_key',
    'validate_api_key_and_source'
]

LOG = logging.getLogger(__name__)


def validate_token(token_string):
    """
    Validate the provided authentication token.

    :param token_string: Authentication token provided.
    :type token_string: ``str``

    :return: TokenDB object on success.
    :rtype: :class:`.TokenDB`
    """
    token = Token.get(token_string)

    if token.expiry <= date_utils.get_datetime_utc_now():
        # TODO: purge expired tokens
        LOG.audit('Token with id "%s" has expired.' % (token.id))
        raise exceptions.TokenExpiredError('Token has expired.')

    LOG.audit('Token with id "%s" is validated.' % (token.id))

    return token


def validate_token_and_source(token_in_headers, token_in_query_params):
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

    return validate_token(token_in_headers or token_in_query_params)


def generate_api_key():
    """
    Generates an sufficiently large and random key.

    credit: http://jetfar.com/simple-api-key-generation-in-python/
    """
    # 256bit seed from urandom
    seed = os.urandom(256)
    # since urandom does not provide sufficient entropy hash, base64encode and salt.
    # The resulting value is now large and should be hard to predict.
    hashed_seed = hashlib.sha256(seed).hexdigest()
    return base64.b64encode(
        hashed_seed,
        random.choice(['rA', 'aZ', 'gQ', 'hH', 'hG', 'aR', 'DD'])).rstrip('==')


def generate_api_key_and_hash():
    api_key = generate_api_key()
    api_key_hash = hash_utils.hash(api_key)
    return api_key, api_key_hash


def validate_api_key(api_key):
    """
    Validate the provided API key.

    :param api_key: API key provided.
    :type api_key: ``str``

    :return: TokenDB object on success.
    :rtype: :class:`.ApiKeyDB`
    """
    api_key_db = ApiKey.get(api_key)

    if not api_key_db.enabled:
        raise exceptions.ApiKeyDisabledError('API key is disabled.')

    LOG.audit('API key with id "%s" is validated.' % (api_key_db.id))

    return api_key_db


def validate_api_key_and_source(api_key_in_headers, api_key_query_params):
    """
    Validate the provided API key.

    :param api_key_in_headers: API key provided via headers.
    :type api_key_in_headers: ``str``

    :param api_key_query_params: API key provided via query params.
    :type api_key_query_params: ``str``

    :return: TokenDB object on success.
    :rtype: :class:`.ApiKeyDB`
    """
    if not api_key_in_headers and not api_key_query_params:
        LOG.audit('API key is not found in header or query parameters.')
        raise exceptions.ApiKeyNotProvidedError('API key is not provided.')

    if api_key_in_headers:
        LOG.audit('API key provided in headers')

    if api_key_query_params:
        LOG.audit('API key provided in query parameters')

    return validate_api_key(api_key_in_headers or api_key_query_params)
