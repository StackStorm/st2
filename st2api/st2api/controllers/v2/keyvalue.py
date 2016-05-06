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

from pecan import abort
import six

from st2common import log as logging
from st2common.constants.keyvalue import ALLOWED_SCOPES
from st2common.models.api.base import jsexpose

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)

__all__ = [
    'ScopedKeyValuePairController'
]


class ScopedKeyValuePairController(object):
    """
    Implements the REST endpoint for managing the scoped key value store.
    """

    @jsexpose
    def _lookup(self, *remainder):
        LOG.info('Hitting lookup method!!!')
        scope = remainder[0]
        if not self._is_allowed_scope(scope):
            msg = 'Scope %s is not in allowed scopes list: %s.' % (scope, ALLOWED_SCOPES)
            abort(http_client.BAD_REQUEST, msg)
            return
        LOG.info('Got a valid scope. Now should route to key value controller.')
        return {'dummy': 'silly'}

    @staticmethod
    def _is_allowed_scope(scope):
        return scope in ALLOWED_SCOPES
