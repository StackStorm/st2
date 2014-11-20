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

try:
    import simplejson as json
except ImportError:
    import json

import pecan
import six
from urlparse import urljoin

from st2common import log as logging
from st2common.models.base import jsexpose

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)


class WebhooksController(pecan.rest.RestController):
    def __init__(self, *args, **kwargs):
        super(WebhooksController, self).__init__(*args, **kwargs)
        self._hooks = {'shit'}
        self._base_url = '/webhooks'

    @jsexpose(str, status_code=http_client.ACCEPTED)
    def post(self, hook, **kwargs):
        LOG.info('POST /webhooks/ with hook=%s', hook)

        if hook not in self._hooks:
            msg = 'Webhook %s not registered with st2' % hook
            return pecan.abort(http_client.NOT_FOUND, msg)

        body = pecan.request.body
        try:
            body = json.loads(body)
        except ValueError:
            msg = 'Invalid JSON body %s' % body
            return pecan.abort(http_client.BAD_REQUEST, msg)

        # TODO: Dispatch trigger and payload.
        return body

    # Figure out how to call these. TriggerWatcher?
    def add_trigger(self, trigger):
        url = trigger['parameters']['url']
        self._log.info('Listening to endpoint: %s', urljoin(self._base_url, url))
        self._hooks[url] = trigger

    def update_trigger(self, trigger):
        pass

    def remove_trigger(self, trigger):
        url = trigger['parameters']['url']
        self._log.info('Stop listening to endpoint: %s', urljoin(self._base_url, url))
        del self._hooks[url]

    def _get_headers_as_dict(self, headers):
        headers_dict = {}
        for key, value in headers:
            headers_dict[key] = value
        return headers_dict
