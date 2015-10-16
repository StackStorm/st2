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

import six
import pecan
import uuid
from pecan import abort
from pecan.rest import RestController
from six.moves.urllib import parse as urlparse
urljoin = urlparse.urljoin

from st2common import log as logging
from st2common.constants.triggers import WEBHOOK_TRIGGER_TYPES
from st2common.models.api.base import jsexpose
from st2common.models.api.trace import TraceContext
import st2common.services.triggers as trigger_service
from st2common.services.triggerwatcher import TriggerWatcher
from st2common.transport.reactor import TriggerDispatcher
from st2common.rbac.types import PermissionType
from st2common.rbac.decorators import request_user_has_webhook_permission

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)

TRACE_TAG_HEADER = 'St2-Trace-Tag'


class WebhooksController(RestController):
    def __init__(self, *args, **kwargs):
        super(WebhooksController, self).__init__(*args, **kwargs)
        self._hooks = {}
        self._base_url = '/webhooks/'
        self._trigger_types = WEBHOOK_TRIGGER_TYPES.keys()

        self._trigger_dispatcher = TriggerDispatcher(LOG)
        self._trigger_watcher = TriggerWatcher(create_handler=self._handle_create_trigger,
                                               update_handler=self._handle_update_trigger,
                                               delete_handler=self._handle_delete_trigger,
                                               trigger_types=self._trigger_types,
                                               queue_suffix='webhooks',
                                               exclusive=True)
        self._trigger_watcher.start()
        self._register_webhook_trigger_types()

    @jsexpose()
    def get_all(self):
        # Return only the hooks known by this controller.
        return [trigger for trigger in six.itervalues(self._hooks)]

    @jsexpose()
    def get_one(self, name):
        hook = self._hooks.get(name, None)

        if not hook:
            abort(http_client.NOT_FOUND)
            return

        return hook

    @request_user_has_webhook_permission(permission_type=PermissionType.WEBHOOK_SEND)
    @jsexpose(arg_types=[str], status_code=http_client.ACCEPTED)
    def post(self, *args, **kwargs):
        hook = '/'.join(args)  # TODO: There must be a better way to do this.
        body = pecan.request.body
        try:
            body = json.loads(body)
        except ValueError:
            self._log_request('Invalid JSON body.', pecan.request)
            msg = 'Invalid JSON body: %s' % (body)
            return pecan.abort(http_client.BAD_REQUEST, msg)

        headers = self._get_headers_as_dict(pecan.request.headers)
        # If webhook contains a trace-tag use that else create create a unique trace-tag.
        trace_context = self._create_trace_context(trace_tag=headers.pop(TRACE_TAG_HEADER, None),
                                                   hook=hook)

        if hook == 'st2' or hook == 'st2/':
            return self._handle_st2_webhook(body, trace_context=trace_context)

        if not self._is_valid_hook(hook):
            self._log_request('Invalid hook.', pecan.request)
            msg = 'Webhook %s not registered with st2' % hook
            return pecan.abort(http_client.NOT_FOUND, msg)

        trigger = self._get_trigger_for_hook(hook)
        payload = {}

        payload['headers'] = headers
        payload['body'] = body
        self._trigger_dispatcher.dispatch(trigger, payload=payload, trace_context=trace_context)

        return body

    def _handle_st2_webhook(self, body, trace_context):
        trigger = body.get('trigger', None)
        payload = body.get('payload', None)
        if not trigger:
            msg = 'Trigger not specified.'
            return pecan.abort(http_client.BAD_REQUEST, msg)
        self._trigger_dispatcher.dispatch(trigger, payload=payload, trace_context=trace_context)

        return body

    def _is_valid_hook(self, hook):
        # TODO: Validate hook payload with payload_schema.
        return hook in self._hooks

    def _get_trigger_for_hook(self, hook):
        return self._hooks[hook]

    def _register_webhook_trigger_types(self):
        for trigger_type in WEBHOOK_TRIGGER_TYPES.values():
            trigger_service.create_trigger_type_db(trigger_type)

    def _create_trace_context(self, trace_tag, hook):
        # if no trace_tag then create a unique one
        if not trace_tag:
            trace_tag = 'webhook-%s-%s' % (hook, uuid.uuid4().hex)
        return TraceContext(trace_tag=trace_tag)

    def add_trigger(self, trigger):
        # Note: Permission checking for creating and deleting a webhook is done during rule
        # creation
        url = trigger['parameters']['url']
        LOG.info('Listening to endpoint: %s', urljoin(self._base_url, url))
        self._hooks[url] = trigger

    def update_trigger(self, trigger):
        pass

    def remove_trigger(self, trigger):
        # Note: Permission checking for creating and deleting a webhook is done during rule
        # creation
        url = trigger['parameters']['url']

        if url in self._hooks:
            LOG.info('Stop listening to endpoint: %s', urljoin(self._base_url, url))
            del self._hooks[url]

    def _get_headers_as_dict(self, headers):
        headers_dict = {}
        for key, value in headers.items():
            headers_dict[key] = value
        return headers_dict

    def _log_request(self, msg, request, log_method=LOG.debug):
        headers = self._get_headers_as_dict(request.headers)
        body = str(request.body)
        log_method('%s\n\trequest.header: %s.\n\trequest.body: %s.', msg, headers, body)

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
