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

from oslo.config import cfg
from pecan.hooks import PecanHook

from st2common import log as logging


LOG = logging.getLogger(__name__)


class CorsHook(PecanHook):

    def after(self, state):
        headers = state.response.headers

        origin = state.request.headers.get('Origin')
        origins = cfg.CONF.api.allow_origin
        if origin:
            if '*' in origins:
                origin_allowed = '*'
            else:
                # See http://www.w3.org/TR/cors/#access-control-allow-origin-response-header
                origin_allowed = origin if origin in origins else 'null'
        else:
            origin_allowed = origins[0] if len(origins) > 0 else 'http://localhost:3000'

        methods_allowed = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
        request_headers_allowed = ['Content-Type', 'Authorization']
        response_headers_allowed = ['Content-Type', 'X-Limit', 'X-Total-Count']

        headers['Access-Control-Allow-Origin'] = origin_allowed
        headers['Access-Control-Allow-Methods'] = ','.join(methods_allowed)
        headers['Access-Control-Allow-Headers'] = ','.join(request_headers_allowed)
        headers['Access-Control-Expose-Headers'] = ','.join(response_headers_allowed)
        if not headers['Content-Length']:
            headers['Content-Length'] = str(len(state.response.body))
