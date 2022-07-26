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
import uuid
import datetime

from oslo_config import cfg

from st2common.util import isotime
from st2common.util import date as date_utils
from st2common.exceptions.auth import (
    TokenNotFoundError,
    UserNotFoundError,
)
from st2common.exceptions.auth import TTLTooLargeException
from st2common.models.db.auth import SSORequestDB, TokenDB, UserDB
from st2common.persistence.auth import SSORequest, Token, User
from st2common import log as logging

__all__ = [
    "create_token",
    "delete_token",
    "create_cli_sso_request",
    "create_web_sso_request",
    "get_sso_request_by_request_id",
]

LOG = logging.getLogger(__name__)

DEFAULT_SSO_REQUEST_TTL = 120


def create_token(
    username, ttl=None, metadata=None, add_missing_user=True, service=False
):
    """
    :param username: Username of the user to create the token for. If the account for this user
                     doesn't exist yet it will be created.
    :type username: ``str``

    :param ttl: Token TTL (in seconds).
    :type ttl: ``int``

    :param metadata: Optional metadata to associate with the token.
    :type metadata: ``dict``

    :param add_missing_user: Add the user given by `username` if they don't exist
    :type  add_missing_user: ``bool``

    :param service: True if this is a service (non-user) token.
    :type service: ``bool``
    """

    if ttl:
        # Note: We allow arbitrary large TTLs for service tokens.
        if not service and ttl > cfg.CONF.auth.token_ttl:
            msg = "TTL specified %s is greater than max allowed %s." % (
                ttl,
                cfg.CONF.auth.token_ttl,
            )
            raise TTLTooLargeException(msg)
    else:
        ttl = cfg.CONF.auth.token_ttl

    if username:
        try:
            User.get_by_name(username)
        except:
            if add_missing_user:
                user_db = UserDB(name=username)
                User.add_or_update(user_db)

                extra = {"username": username, "user": user_db}
                LOG.audit('Registered new user "%s".' % (username), extra=extra)
            else:
                raise UserNotFoundError()

    token = uuid.uuid4().hex
    expiry = date_utils.get_datetime_utc_now() + datetime.timedelta(seconds=ttl)
    token = TokenDB(
        user=username, token=token, expiry=expiry, metadata=metadata, service=service
    )
    Token.add_or_update(token)

    username_string = username if username else "an anonymous user"
    token_expire_string = isotime.format(expiry, offset=False)
    extra = {"username": username, "token_expiration": token_expire_string}

    LOG.audit(
        'Access granted to "%s" with the token set to expire at "%s".'
        % (username_string, token_expire_string),
        extra=extra,
    )

    return token


def delete_token(token):
    try:
        token_db = Token.get(token)
        return Token.delete(token_db)
    except TokenNotFoundError:
        pass
    except Exception:
        raise


def create_cli_sso_request(request_id, key, ttl=DEFAULT_SSO_REQUEST_TTL):
    """
    :param request_id: ID of the SSO request that is being created (usually uuid format prepended by _)
    :type request_id: ``str``

    :param key: Symmetric key used to encrypt/decrypt the request between the CLI and the server
    :type key: ``str``

    :param ttl: SSO request TTL (in seconds).
    :type ttl: ``int``
    """

    return _create_sso_request(request_id, ttl, SSORequestDB.Type.CLI, key=key)


def create_web_sso_request(request_id, ttl=DEFAULT_SSO_REQUEST_TTL):
    """
    :param request_id: ID of the SSO request that is being created (usually uuid format prepended by _)
    :type request_id: ``str``

    :param ttl: SSO request TTL (in seconds).
    :type ttl: ``int``
    """

    return _create_sso_request(request_id, ttl, SSORequestDB.Type.WEB)


def _create_sso_request(request_id, ttl, type, **kwargs) -> SSORequestDB:

    expiry = date_utils.get_datetime_utc_now() + datetime.timedelta(seconds=ttl)

    request = SSORequestDB(request_id=request_id, expiry=expiry, type=type, **kwargs)
    SSORequest.add_or_update(request)

    expire_string = isotime.format(expiry, offset=False)

    LOG.audit(
        'Created SAML request with ID "%s" set to expire at "%s" of type "%s".'
        % (request_id, expire_string, type)
    )

    return request


def get_sso_request_by_request_id(request_id) -> SSORequestDB:
    request_db = SSORequest.get_by_request_id(request_id)
    return request_db
