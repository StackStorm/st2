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
from st2common.constants.triggers import GENERIC_WEBHOOK_TRIGGER_REF
from st2common.models.base import jsexpose
from st2common.services.triggerwatcher import TriggerWatcher
from st2common.transport.reactor import TriggerDispatcher

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)


class WebhooksController(pecan.rest.RestController):
    def __init__(self, *args, **kwargs):
        super(WebhooksController, self).__init__(*args, **kwargs)
        self._hooks = {}
        self._base_url = '/webhooks/'
        self._trigger_types = [GENERIC_WEBHOOK_TRIGGER_REF]

        self._trigger_dispatcher = TriggerDispatcher(LOG)
        self._trigger_watcher = TriggerWatcher(create_handler=self._handle_create_trigger,
                                               update_handler=self._handle_update_trigger,
                                               delete_handler=self._handle_delete_trigger,
                                               trigger_types=self._trigger_types)
        self._trigger_watcher.start()

    @jsexpose(str, status_code=http_client.ACCEPTED)
    def post(self, *args, **kwargs):
        hook = '/'.join(args)  # TODO: There must be a better way to do this.
        LOG.info('POST /webhooks/ with hook=%s', hook)

        body = pecan.request.body
        try:
            body = json.loads(body)
        except ValueError:
            msg = 'Invalid JSON body: %s' % (body)
            return pecan.abort(http_client.BAD_REQUEST, msg)

        if hook == 'st2':
            return self._handle_st2_webhook(body)

        if not self._is_valid_hook(hook):
            msg = 'Webhook %s not registered with st2' % hook
            return pecan.abort(http_client.NOT_FOUND, msg)

        trigger = self._get_trigger_for_hook(hook)
        payload = {}
        payload['headers'] = self._get_headers_as_dict(pecan.request.headers)
        payload['body'] = body
        self._trigger_dispatcher.dispatch(trigger, payload=payload)

        return body

    def _handle_st2_webhook(self, body):
        trigger = body.get('trigger', None)
        payload = body.get('payload', None)
        if not trigger:
            msg = 'Trigger not specified.'
            return pecan.abort(http_client.BAD_REQUEST, msg)
        self._trigger_dispatcher.dispatch(trigger, payload=payload)

        return body

    def _is_valid_hook(self, hook):
        # TODO: Validate hook payload with payload_schema.
        return hook in self._hooks

    def _get_trigger_for_hook(self, hook):
        return self._hooks[hook]

    def add_trigger(self, trigger):
        url = trigger['parameters']['url']
        LOG.info('Listening to endpoint: %s', urljoin(self._base_url, url))
        self._hooks[url] = trigger

    def update_trigger(self, trigger):
        pass

    def remove_trigger(self, trigger):
        url = trigger['parameters']['url']

        if url in self._hooks:
            LOG.info('Stop listening to endpoint: %s', urljoin(self._base_url, url))
            del self._hooks[url]

    def _get_headers_as_dict(self, headers):
        headers_dict = {}
        for key, value in headers.items():
            headers_dict[key] = value
        return headers_dict

    ##############################################
    # Event handler methods for the trigger events
    ##############################################

    def _handle_create_trigger(self, trigger):
        LOG.debug('Calling "add_trigger" method (trigger.type=%s)' % (trigger.type))
        trigger = self._sanitize_trigger(trigger=trigger)
        self.add_trigger(trigger=trigger)

    def _handle_update_trigger(self, trigger):
        LOG.debug('Calling "update_trigger" method (trigger.type=%s)' % (trigger.type))
        trigger = self._sanitize_trigger(trigger=trigger)
        self.update_trigger(trigger=trigger)

    def _handle_delete_trigger(self, trigger):
        LOG.debug('Calling "remove_trigger" method (trigger.type=%s)' % (trigger.type))
        trigger = self._sanitize_trigger(trigger=trigger)
        self.remove_trigger(trigger=trigger)

    def _sanitize_trigger(self, trigger):
        sanitized = trigger._data
        if 'id' in sanitized:
            # Friendly objectid rather than the MongoEngine representation.
            sanitized['id'] = str(sanitized['id'])
        return sanitized
