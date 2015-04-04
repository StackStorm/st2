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

import eventlet
from kombu import Connection
from kombu.mixins import ConsumerMixin
from oslo.config import cfg

from st2common import log as logging
from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED, LIVEACTION_STATUS_FAILED
from st2common.constants.triggers import INTERNAL_TRIGGER_TYPES
from st2common.models.system.common import ResourceReference
from st2common.transport import liveaction, publishers
from st2common.transport.reactor import TriggerDispatcher
from st2common.util.greenpooldispatch import BufferedDispatcher

LOG = logging.getLogger(__name__)

ACTIONUPDATE_WORK_Q = liveaction.get_queue('st2.notifiers.work',
                                           routing_key=publishers.UPDATE_RK)
ACTION_COMPLETE_STATES = [LIVEACTION_STATUS_FAILED, LIVEACTION_STATUS_SUCCEEDED]
ACTION_SENSOR_ENABLED = cfg.CONF.action_sensor.enable
ACTION_TRIGGER_TYPE = INTERNAL_TRIGGER_TYPES['action'][0]


class LiveActionUpdateQueueConsumer(ConsumerMixin):
    def __init__(self, connection, notifier):
        self.connection = connection
        self._dispatcher = BufferedDispatcher()
        self._notifier = notifier

    def shutdown(self):
        self._dispatcher.shutdown()

    def get_consumers(self, Consumer, channel):
        consumer = Consumer(queues=[ACTIONUPDATE_WORK_Q],
                            accept=['pickle'],
                            callbacks=[self.process_task])
        # use prefetch_count=1 for fair dispatch. This way workers that finish an item get the next
        # task and the work does not get queued behind any single large item.
        consumer.qos(prefetch_count=1)
        return [consumer]

    def process_task(self, body, message):
        LOG.debug('process_task')
        LOG.debug('     body: %s', body)
        LOG.debug('     message.properties: %s', message.properties)
        LOG.debug('     message.delivery_info: %s', message.delivery_info)
        try:
            self._dispatcher.dispatch(self._do_process_task, body)
        finally:
            message.ack()

    def _do_process_task(self, body):
        try:
            if body.status in ACTION_COMPLETE_STATES:
                self._notifier.handle_action_complete(body)
        except:
            LOG.exception('Add query_context failed. Message body : %s', body)


class Notifier(object):
    def __init__(self, q_connection=None):
        self._queue_consumer = LiveActionUpdateQueueConsumer(q_connection, self)
        self._consumer_thread = None
        self._trigger_dispatcher = TriggerDispatcher(LOG)

    def start(self):
        self._consumer_thread = eventlet.spawn(self._queue_consumer.run)
        self._consumer_thread.wait()

    def handle_action_complete(self, liveaction):
        if liveaction.notify is not None:
            self._post_notify_triggers(liveaction)
        else:
            self._post_generic_trigger(liveaction)

    def _post_notify_triggers(self, liveaction):
        notify = getattr(liveaction, 'notify', None)

        if not notify:
            return

        if notify.on_complete:
            self._post_notify_subsection_triggers(
                liveaction, notify.on_complete, default_message_suffix='completed.')
        if liveaction.status == LIVEACTION_STATUS_SUCCEEDED and notify.on_success:
            self._post_notify_subsection_triggers(
                liveaction, notify.on_success, default_message_suffix='succeeded.')
        if liveaction.status == LIVEACTION_STATUS_FAILED and notify.on_failure:
            self._post_notify_subsection_triggers(
                liveaction, notify.on_failure, default_message_suffix='failed.')

    def _post_notify_subsection_triggers(self, liveaction, notify_subsection,
                                         default_message_suffix):
        if notify_subsection.triggers and len(notify_subsection.triggers) >= 1:
            message = notify_subsection.message or (
                'Action ' + liveaction.action + ' ' + default_message_suffix)
            data = notify_subsection.data  # XXX: Handle Jinja
            if not data:
                data = {'result': liveaction.result}
            data['execution_id'] = str(liveaction.id)
            data['status'] = liveaction.status

            payload = {}
            payload['message'] = message
            payload['data'] = data

            for trigger in notify_subsection.triggers:
                try:
                    self._trigger_dispatcher.dispatch(trigger, payload=payload)
                except:
                    LOG.exception('Failed to fire trigger for liveaction %s.', str(liveaction.id))

    def _post_generic_trigger(self, liveaction):
        if not ACTION_SENSOR_ENABLED:
            return

        try:
            trigger = ResourceReference.to_string_reference(pack=ACTION_TRIGGER_TYPE['pack'],
                                                            name=ACTION_TRIGGER_TYPE['name'])
            payload = {'execution_id': str(liveaction.id),
                       'status': liveaction.status,
                       'start_timestamp': str(liveaction.start_timestamp),
                       'action_name': liveaction.action,
                       'parameters': liveaction.parameters,
                       'result': liveaction.result}
            LOG.debug('POSTing %s for %s. Payload - %s.', ACTION_TRIGGER_TYPE['name'],
                      liveaction.id, payload)
            self._trigger_dispatcher.dispatch(trigger, payload=payload)
        except:
            LOG.exception('Failed to fire trigger for liveaction %s.', str(liveaction.id))


def get_notifier():
    with Connection(cfg.CONF.messaging.url) as conn:
        notifier = Notifier(q_connection=conn)
        return notifier
