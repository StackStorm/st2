# -*- coding: utf-8 -*-
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

import logging
import six

from orchestra import exceptions as exc

from st2common.persistence import auth as auth_db_access
from st2common.util import keyvalue as kvp_util


LOG = logging.getLogger(__name__)


def st2kv_(context, key, decrypt=False):
    if not isinstance(key, six.string_types):
        raise TypeError('Given key is not typeof string.')

    if not isinstance(decrypt, bool):
        raise TypeError('Decrypt parameter is not typeof bool.')

    try:
        username = context['__vars']['st2']['user']
    except KeyError:
        raise KeyError('Could not get user from context.')

    try:
        user_db = auth_db_access.User.get(username)
    except Exception as e:
        raise Exception('Failed to retrieve User object for user "%s" % (username)' % (str(e)))

    LOG.debug('ST2KV Decrypt: %s', decrypt)

    kvp = kvp_util.get_key(key=key, user_db=user_db, decrypt=decrypt)

    if not kvp:
        raise exc.ExpressionEvaluationException(
            'Key %s does not exist in StackStorm datastore.' % key
        )

    return kvp
