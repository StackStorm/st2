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

import uuid
import datetime

from oslo.config import cfg

from st2common.util import isotime
from st2common.exceptions.auth import TokenNotFoundError
from st2common.exceptions.auth import TTLTooLargeException
from st2common.models.db.auth import TokenDB, UserDB
from st2common.persistence.auth import Token, User
from st2common import log as logging

__all__ = [
    'create_token',
    'delete_token'
]

LOG = logging.getLogger(__name__)


def create_token(username, ttl=None, metadata=None):
    """
    :param username: Username of the user to create the token for. If the account for this user
                     doesn't exist yet it will be created.
    :type username: ``str``

    :param ttl: Token TTL (in seconds).
    :type ttl: ``int``

    :param metadata: Optional metadata to associate with the token.
    :type metadata: ``dict``
    """

    if ttl:
        if ttl > cfg.CONF.auth.token_ttl:
            msg = 'TTL specified %s is greater than max allowed %s.' % (
                ttl, cfg.CONF.auth.token_ttl
            )
            raise TTLTooLargeException(msg)
    else:
        ttl = cfg.CONF.auth.token_ttl

    if username:
        try:
            User.get_by_name(username)
        except:
            user = UserDB(name=username)
            User.add_or_update(user)

            extra = {'username': username, 'user': user}
            LOG.audit('Registered new user "%s".' % (username), extra=extra)

    token = uuid.uuid4().hex
    expiry = isotime.get_datetime_utc_now() + datetime.timedelta(seconds=ttl)
    token = TokenDB(user=username, token=token, expiry=expiry, metadata=metadata)
    Token.add_or_update(token)

    username_string = username if username else 'an anonymous user'
    token_expire_string = isotime.format(expiry, offset=False)
    extra = {'username': username, 'token_expiration': token_expire_string}

    LOG.audit('Access granted to "%s" with the token set to expire at "%s".' %
              (username_string, token_expire_string), extra=extra)

    return token


def delete_token(token):
    try:
        token_db = Token.get(token)
        return Token.delete(token_db)
    except TokenNotFoundError:
        pass
    except Exception:
        raise
