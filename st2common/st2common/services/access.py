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
from st2common.models.db.access import TokenDB, UserDB
from st2common.persistence.access import Token, User
from st2common import log as logging


LOG = logging.getLogger(__name__)


def create_token(username, ttl=None):
    if not ttl or ttl > cfg.CONF.auth.token_ttl:
        ttl = cfg.CONF.auth.token_ttl

    if username:
        try:
            User.get_by_name(username)
        except:
            user = UserDB(name=username)
            User.add_or_update(user)
            LOG.audit('Registered new user "%s".' % username)
        LOG.audit('Access granted to user "%s".' % username)

    token = uuid.uuid4().hex
    expiry = datetime.datetime.utcnow() + datetime.timedelta(seconds=ttl)
    expiry = isotime.add_utc_tz(expiry)
    token = TokenDB(user=username, token=token, expiry=expiry)
    Token.add_or_update(token)
    LOG.audit('Access granted to %s with the token set to expire at "%s".' %
              ('user "%s"' % username if username else "an anonymous user",
               isotime.format(expiry, offset=False)))

    return token


def delete_token(token):
    token_db = Token.get(token)
    return Token.delete(token_db)
