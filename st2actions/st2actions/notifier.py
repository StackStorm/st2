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

import json

from kombu import Connection
from oslo.config import cfg

from st2common import log as logging
from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED, LIVEACTION_STATUS_FAILED
from st2common.constants.triggers import INTERNAL_TRIGGER_TYPES
from st2common.models.db.liveaction import LiveActionDB
from st2common.persistence.action import Action
from st2common.persistence.policy import Policy
from st2common import policies
from st2common.models.system.common import ResourceReference
from st2common.persistence.execution import ActionExecution
from st2common.transport import consumers, liveaction, publishers
from st2common.transport.reactor import TriggerDispatcher


LOG = logging.getLogger(__name__)

ACTIONUPDATE_WORK_Q = liveaction.get_queue('st2.notifiers.work',
                                           routing_key=publishers.UPDATE_RK)
ACTION_COMPLETE_STATES = [LIVEACTION_STATUS_FAILED, LIVEACTION_STATUS_SUCCEEDED]
ACTION_SENSOR_ENABLED = cfg.CONF.action_sensor.enable
# XXX: Fix this nasty positional dependency.
ACTION_TRIGGER_TYPE = INTERNAL_TRIGGER_TYPES['action'][0]
NOTIFY_TRIGGER_TYPE = INTERNAL_TRIGGER_TYPES['action'][1]


class Notifier(consumers.MessageHandler):
    message_type = LiveActionDB

    def __init__(self, connection, queues, trigger_dispatcher=None):
        super(Notifier, self).__init__(connection, queues)
        self._trigger_dispatcher = trigger_dispatcher
        self._notify_trigger = ResourceReference.to_string_reference(
            pack=NOTIFY_TRIGGER_TYPE['pack'],
            name=NOTIFY_TRIGGER_TYPE['name'])
        self._action_trigger = ResourceReference.to_string_reference(
            pack=ACTION_TRIGGER_TYPE['pack'],
            name=ACTION_TRIGGER_TYPE['name'])

    def process(self, liveaction):
        if liveaction.status not in ACTION_COMPLETE_STATES:
            return

        execution_id = self._get_execution_id(liveaction)

        self._apply_post_run_policies(liveaction=liveaction, execution_id=execution_id)

        if liveaction.notify is not None:
            self._post_notify_triggers(liveaction=liveaction, execution_id=execution_id)

        self._post_generic_trigger(liveaction=liveaction, execution_id=execution_id)

    def _get_execution_id(self, liveaction):
        try:
            execution = ActionExecution.get(liveaction__id=str(liveaction.id))
            return str(execution.id)
        except:
            LOG.exception('Execution object corresponding to LiveAction %s not found.',
                          str(liveaction.id))
            return None

    def _post_notify_triggers(self, liveaction=None, execution_id=None):
        notify = getattr(liveaction, 'notify', None)

        if not notify:
            return

        if notify.on_complete:
            self._post_notify_subsection_triggers(
                liveaction=liveaction, execution_id=execution_id,
                notify_subsection=notify.on_complete,
                default_message_suffix='completed.')
        if liveaction.status == LIVEACTION_STATUS_SUCCEEDED and notify.on_success:
            self._post_notify_subsection_triggers(
                liveaction=liveaction, execution_id=execution_id,
                notify_subsection=notify.on_success,
                default_message_suffix='succeeded.')
        if liveaction.status == LIVEACTION_STATUS_FAILED and notify.on_failure:
            self._post_notify_subsection_triggers(
                liveaction=liveaction, execution_id=execution_id,
                notify_subsection=notify.on_failure,
                default_message_suffix='failed.')

    def _post_notify_subsection_triggers(self, liveaction=None, execution_id=None,
                                         notify_subsection=None,
                                         default_message_suffix=None):
        if notify_subsection.channels and len(notify_subsection.channels) >= 1:
            payload = {}
            message = notify_subsection.message or (
                'Action ' + liveaction.action + ' ' + default_message_suffix)
            data = notify_subsection.data or {}  # XXX: Handle Jinja
            # At this point convert result to a string. This restricts the rulesengines
            # ability to introspect the result. On the other handle atleast a json usable
            # result is sent as part of the notification. If jinja is required to convert
            # to a string representation it uses str(...) which make it impossible to
            # parse the result as json any longer.
            data['result'] = json.dumps(liveaction.result)

            payload['message'] = message
            payload['data'] = data
            payload['execution_id'] = execution_id
            payload['status'] = liveaction.status
            payload['start_timestamp'] = str(liveaction.start_timestamp)
            payload['end_timestamp'] = str(liveaction.end_timestamp)
            payload['action_ref'] = liveaction.action
            payload['runner_ref'] = self._get_runner(liveaction.action)

            failed_channels = []
            for channel in notify_subsection.channels:
                try:
                    payload['channel'] = channel
                    LOG.debug('POSTing %s for %s. Payload - %s.', NOTIFY_TRIGGER_TYPE['name'],
                              liveaction.id, payload)
                    self._trigger_dispatcher.dispatch(self._notify_trigger, payload=payload)
                except:
                    failed_channels.append(channel)

            if len(failed_channels) > 0:
                raise Exception('Failed notifications to channels: %s' % ', '.join(failed_channels))

    def _post_generic_trigger(self, liveaction=None, execution_id=None):
        if not ACTION_SENSOR_ENABLED:
            return

        payload = {'execution_id': execution_id,
                   'status': liveaction.status,
                   'start_timestamp': str(liveaction.start_timestamp),
                   # deprecate 'action_name' at some point and switch to 'action_ref'
                   'action_name': liveaction.action,
                   'action_ref': liveaction.action,
                   'runner_ref': self._get_runner(liveaction.action),
                   'parameters': liveaction.parameters,
                   'result': liveaction.result}
        LOG.debug('POSTing %s for %s. Payload - %s.', ACTION_TRIGGER_TYPE['name'],
                  liveaction.id, payload)
        self._trigger_dispatcher.dispatch(self._action_trigger, payload=payload)

    def _apply_post_run_policies(self, liveaction=None, execution_id=None):
        # Apply policies defined for the action.
        for policy_db in Policy.query(resource_ref=liveaction.action):
            driver = policies.get_driver(policy_db.ref,
                                         policy_db.policy_type,
                                         **policy_db.parameters)

            try:
                liveaction = driver.apply_after(liveaction)
            except:
                LOG.exception('An exception occurred while applying policy "%s".', policy_db.ref)

    def _get_runner(self, action_ref):
        action = Action.get_by_ref(action_ref)
        return action['runner_type']['name']


def get_notifier():
    with Connection(cfg.CONF.messaging.url) as conn:
        return Notifier(conn, [ACTIONUPDATE_WORK_Q], trigger_dispatcher=TriggerDispatcher(LOG))
