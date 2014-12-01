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

import pecan

from pecan import rest
from six.moves import http_client

from st2common.models.base import jsexpose
from st2common.models.api.access import TokenAPI
from st2common.services.access import create_token
from st2common import log as logging


LOG = logging.getLogger(__name__)


class TokenController(rest.RestController):

    @jsexpose(body=TokenAPI, status_code=http_client.CREATED)
    def post(self, request, **kwargs):
        if not pecan.request.remote_user:
            LOG.audit('Access denied to anonymous user.')
            pecan.abort(http_client.UNAUTHORIZED)

        ttl = getattr(request, 'ttl', None)
        tokendb = create_token(pecan.request.remote_user, ttl)

        return TokenAPI.from_model(tokendb)
