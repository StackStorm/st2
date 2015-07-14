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

from pecan import (abort, expose, request, rest)
from six.moves import http_client

# from st2api.controllers import resource
from st2common import log as logging

LOG = logging.getLogger(__name__)


class ActionAliasController(rest.RestController):

    @expose()
    def post(self, action_alias):
        self._redirect(request)

    @expose()
    def put(self, action_alias_ref_or_id, action_alias):
        self._redirect(request)

    @expose()
    def delete(self, action_alias_ref_or_id):
        self._redirect(request)

    def _redirect(self, request_instance):
        redirect_url = request.path_url.replace('/exp/', '/v1/')
        LOG.debug('Redirecting to: %s', redirect_url)
        # In theory, we could redirect using pecan's redirect method but there is
        # a bug that doesn't display the name of the moved location in the body.
        # redirect_path = request.path.replace('/exp/', '/v1')
        # redirect(location=redirect_path, internal=False, request=request,
        #          code=http_client.MOVED_PERMANENTLY)
        msg = 'The resource has been permanently moved to %s.' % redirect_url
        abort(status_code=http_client.MOVED_PERMANENTLY,
              headers={'Location': redirect_url},
              detail=msg,
              comment=msg)
