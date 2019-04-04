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

import six
import uuid
from six.moves.urllib import parse as urlparse  # pylint: disable=import-error
urljoin = urlparse.urljoin

from st2common import log as logging
from st2common.constants.triggers import WEBHOOK_TRIGGER_TYPES
from st2common.models.api.trace import TraceContext
from st2common.models.api.trigger import TriggerAPI
from st2common.models.db.webhook import WebhookDB
import st2common.services.triggers as trigger_service
from st2common.rbac.types import PermissionType
from st2common.rbac.backends import get_rbac_backend
from st2common.services.triggerwatcher import TriggerWatcher
from st2common.services.trigger_dispatcher import TriggerDispatcherService
from st2common.router import abort
from st2common.router import Response
from st2common.util.jsonify import get_json_type_for_python_value

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)

TRACE_TAG_HEADER = 'St2-Trace-Tag'


class HooksHolder(object):
    """
    Maintains a hook to TriggerDB mapping.
    """
    def __init__(self):
        self._triggers_by_hook = {}

    def __contains__(self, key):
        return key in self._triggers_by_hook

    def add_hook(self, hook, trigger):
        if hook not in self._triggers_by_hook:
            self._triggers_by_hook[hook] = []
        self._triggers_by_hook[hook].append(trigger)

    def remove_hook(self, hook, trigger):
        if hook not in self._triggers_by_hook:
            return False
        remove_index = -1
        for idx, item in enumerate(self._triggers_by_hook[hook]):
            if item['id'] == trigger['id']:
                remove_index = idx
                break
        if remove_index < 0:
            return False
        self._triggers_by_hook[hook].pop(remove_index)
        if not self._triggers_by_hook[hook]:
            del self._triggers_by_hook[hook]
        return True

    def get_triggers_for_hook(self, hook):
        return self._triggers_by_hook.get(hook, [])

    def get_all(self):
        triggers = []
        for values in six.itervalues(self._triggers_by_hook):
            triggers.extend(values)
        return triggers


class WebhooksController(object):
    def __init__(self, *args, **kwargs):
        self._hooks = HooksHolder()
        self._base_url = '/webhooks/'
        self._trigger_types = list(WEBHOOK_TRIGGER_TYPES.keys())

        self._trigger_dispatcher_service = TriggerDispatcherService(LOG)
        queue_suffix = self.__class__.__name__
        self._trigger_watcher = TriggerWatcher(create_handler=self._handle_create_trigger,
                                               update_handler=self._handle_update_trigger,
                                               delete_handler=self._handle_delete_trigger,
                                               trigger_types=self._trigger_types,
                                               queue_suffix=queue_suffix,
                                               exclusive=True)
        self._trigger_watcher.start()
        self._register_webhook_trigger_types()

    def get_all(self):
        # Return only the hooks known by this controller.
        return self._hooks.get_all()

    def get_one(self, url, requester_user):
        triggers = self._hooks.get_triggers_for_hook(url)

        if not triggers:
            abort(http_client.NOT_FOUND)
            return

        permission_type = PermissionType.WEBHOOK_VIEW
        rbac_utils = get_rbac_backend().get_utils_class()
        rbac_utils.assert_user_has_resource_db_permission(user_db=requester_user,
                                                          resource_db=WebhookDB(name=url),
                                                          permission_type=permission_type)

        # For demonstration purpose return 1st
        return triggers[0]

    def post(self, hook, webhook_body_api, headers, requester_user):
        body = webhook_body_api.data

        permission_type = PermissionType.WEBHOOK_SEND
        rbac_utils = get_rbac_backend().get_utils_class()
        rbac_utils.assert_user_has_resource_db_permission(user_db=requester_user,
                                                          resource_db=WebhookDB(name=hook),
                                                          permission_type=permission_type)

        headers = self._get_headers_as_dict(headers)

        # If webhook contains a trace-tag use that else create create a unique trace-tag.
        trace_context = self._create_trace_context(trace_tag=headers.pop(TRACE_TAG_HEADER, None),
                                                   hook=hook)

        if hook == 'st2' or hook == 'st2/':
            # When using st2 or system webhook, body needs to always be a dict
            if not isinstance(body, dict):
                type_string = get_json_type_for_python_value(body)
                msg = ('Webhook body needs to be an object, got: %s' % (type_string))
                raise ValueError(msg)

            trigger = body.get('trigger', None)
            payload = body.get('payload', None)

            if not trigger:
                msg = 'Trigger not specified.'
                return abort(http_client.BAD_REQUEST, msg)

            self._trigger_dispatcher_service.dispatch_with_context(trigger=trigger,
                   payload=payload,
                   trace_context=trace_context,
                   throw_on_validation_error=True)
        else:
            if not self._is_valid_hook(hook):
                self._log_request('Invalid hook.', headers, body)
                msg = 'Webhook %s not registered with st2' % hook
                return abort(http_client.NOT_FOUND, msg)

            triggers = self._hooks.get_triggers_for_hook(hook)
            payload = {}

            payload['headers'] = headers
            payload['body'] = body

            # Dispatch trigger instance for each of the trigger found
            for trigger_dict in triggers:
                # TODO: Instead of dispatching the whole dict we should just
                # dispatch TriggerDB.ref or similar
                self._trigger_dispatcher_service.dispatch_with_context(trigger=trigger_dict,
                   payload=payload,
                   trace_context=trace_context,
                   throw_on_validation_error=True)

        return Response(json=body, status=http_client.ACCEPTED)

    def _is_valid_hook(self, hook):
        # TODO: Validate hook payload with payload_schema.
        return hook in self._hooks

    def _register_webhook_trigger_types(self):
        for trigger_type in WEBHOOK_TRIGGER_TYPES.values():
            trigger_service.create_trigger_type_db(trigger_type)

    def _create_trace_context(self, trace_tag, hook):
        # if no trace_tag then create a unique one
        if not trace_tag:
            trace_tag = 'webhook-%s-%s' % (hook, uuid.uuid4().hex)
        return TraceContext(trace_tag=trace_tag)

    def add_trigger(self, trigger):
        # NOTE: trigger is a dictionary
        # Note: Permission checking for creating and deleting a webhook is done during rule
        # creation
        url = self._get_normalized_url(trigger)
        LOG.info('Listening to endpoint: %s', urljoin(self._base_url, url))
        self._hooks.add_hook(url, trigger)

    def update_trigger(self, trigger):
        pass

    def remove_trigger(self, trigger):
        # Note: Permission checking for creating and deleting a webhook is done during rule
        # creation
        url = self._get_normalized_url(trigger)

        removed = self._hooks.remove_hook(url, trigger)
        if removed:
            LOG.info('Stop listening to endpoint: %s', urljoin(self._base_url, url))

    def _get_normalized_url(self, trigger):
        """
        remove the trailing and leading / so that the hook url and those coming
        from trigger parameters end up being the same.
        """
        return trigger['parameters']['url'].strip('/')

    def _get_headers_as_dict(self, headers):
        headers_dict = {}
        for key, value in headers.items():
            headers_dict[key] = value
        return headers_dict

    def _log_request(self, msg, headers, body, log_method=LOG.debug):
        headers = self._get_headers_as_dict(headers)
        body = str(body)
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
        sanitized = TriggerAPI.from_model(trigger).to_dict()
        return sanitized


webhooks_controller = WebhooksController()
