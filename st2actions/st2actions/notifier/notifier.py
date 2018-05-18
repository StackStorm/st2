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

from __future__ import absolute_import
from datetime import datetime
import json

from kombu import Connection
from oslo_config import cfg

from st2common import log as logging
from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED
from st2common.constants.action import LIVEACTION_STATUS_PAUSED
from st2common.constants.action import LIVEACTION_FAILED_STATES
from st2common.constants.action import LIVEACTION_COMPLETED_STATES
from st2common.constants.triggers import INTERNAL_TRIGGER_TYPES
from st2common.models.api.trace import TraceContext
from st2common.models.db.execution import ActionExecutionDB
from st2common.persistence.action import Action
from st2common.persistence.liveaction import LiveAction
from st2common.persistence.policy import Policy
from st2common import policies
from st2common.models.system.common import ResourceReference
from st2common.persistence.execution import ActionExecution
from st2common.services import trace as trace_service
from st2common.services import workflows as wf_svc
from st2common.transport import consumers
from st2common.transport import utils as transport_utils
from st2common.transport.reactor import TriggerDispatcher
from st2common.util import isotime
from st2common.util import jinja as jinja_utils
from st2common.constants.action import ACTION_CONTEXT_KV_PREFIX
from st2common.constants.action import ACTION_PARAMETERS_KV_PREFIX
from st2common.constants.action import ACTION_RESULTS_KV_PREFIX
from st2common.constants.keyvalue import FULL_SYSTEM_SCOPE, SYSTEM_SCOPE, DATASTORE_PARENT_SCOPE
from st2common.services.keyvalues import KeyValueLookup
from st2common.transport.queues import NOTIFIER_ACTIONUPDATE_WORK_QUEUE

__all__ = [
    'Notifier',
    'get_notifier'
]

LOG = logging.getLogger(__name__)

ACTION_SENSOR_ENABLED = cfg.CONF.action_sensor.enable
# XXX: Fix this nasty positional dependency.
ACTION_TRIGGER_TYPE = INTERNAL_TRIGGER_TYPES['action'][0]
NOTIFY_TRIGGER_TYPE = INTERNAL_TRIGGER_TYPES['action'][1]


class Notifier(consumers.MessageHandler):
    message_type = ActionExecutionDB

    def __init__(self, connection, queues, trigger_dispatcher=None):
        super(Notifier, self).__init__(connection, queues)
        if not trigger_dispatcher:
            trigger_dispatcher = TriggerDispatcher(LOG)
        self._trigger_dispatcher = trigger_dispatcher
        self._notify_trigger = ResourceReference.to_string_reference(
            pack=NOTIFY_TRIGGER_TYPE['pack'],
            name=NOTIFY_TRIGGER_TYPE['name'])
        self._action_trigger = ResourceReference.to_string_reference(
            pack=ACTION_TRIGGER_TYPE['pack'],
            name=ACTION_TRIGGER_TYPE['name'])

    def process(self, execution_db):
        execution_id = str(execution_db.id)
        extra = {'execution': execution_db}
        LOG.debug('Processing execution %s', execution_id, extra=extra)

        if ('orchestra' in execution_db.context and
                execution_db.status == LIVEACTION_STATUS_PAUSED):
            wf_svc.handle_action_execution_pause(execution_db)

        if execution_db.status not in LIVEACTION_COMPLETED_STATES:
            LOG.debug('Skipping processing of execution %s since it\'s not in a completed state' %
                      (execution_id), extra=extra)
            return

        liveaction_id = execution_db.liveaction['id']
        liveaction_db = LiveAction.get_by_id(liveaction_id)
        self._apply_post_run_policies(liveaction_db=liveaction_db)

        if liveaction_db.notify is not None:
            self._post_notify_triggers(liveaction_db=liveaction_db, execution_db=execution_db)

        self._post_generic_trigger(liveaction_db=liveaction_db, execution_db=execution_db)

        if 'orchestra' in liveaction_db.context:
            wf_svc.handle_action_execution_completion(execution_db)

    def _get_execution_for_liveaction(self, liveaction):
        execution = ActionExecution.get(liveaction__id=str(liveaction.id))

        if not execution:
            return None

        return execution

    def _post_notify_triggers(self, liveaction_db=None, execution_db=None):
        notify = getattr(liveaction_db, 'notify', None)

        if not notify:
            return

        if notify.on_complete:
            self._post_notify_subsection_triggers(
                liveaction_db=liveaction_db, execution_db=execution_db,
                notify_subsection=notify.on_complete,
                default_message_suffix='completed.')
        if liveaction_db.status == LIVEACTION_STATUS_SUCCEEDED and notify.on_success:
            self._post_notify_subsection_triggers(
                liveaction_db=liveaction_db, execution_db=execution_db,
                notify_subsection=notify.on_success,
                default_message_suffix='succeeded.')
        if liveaction_db.status in LIVEACTION_FAILED_STATES and notify.on_failure:
            self._post_notify_subsection_triggers(
                liveaction_db=liveaction_db, execution_db=execution_db,
                notify_subsection=notify.on_failure,
                default_message_suffix='failed.')

    def _post_notify_subsection_triggers(self, liveaction_db=None, execution_db=None,
                                         notify_subsection=None,
                                         default_message_suffix=None):
        routes = (getattr(notify_subsection, 'routes') or
                  getattr(notify_subsection, 'channels', None))

        execution_id = str(execution_db.id)

        if routes and len(routes) >= 1:
            payload = {}
            message = notify_subsection.message or (
                'Action ' + liveaction_db.action + ' ' + default_message_suffix)
            data = notify_subsection.data or {}

            jinja_context = self._build_jinja_context(
                liveaction_db=liveaction_db, execution_db=execution_db
            )

            try:
                message = self._transform_message(message=message,
                                                  context=jinja_context)
            except:
                LOG.exception('Failed (Jinja) transforming `message`.')

            try:
                data = self._transform_data(data=data, context=jinja_context)
            except:
                LOG.exception('Failed (Jinja) transforming `data`.')

            # At this point convert result to a string. This restricts the rulesengines
            # ability to introspect the result. On the other handle atleast a json usable
            # result is sent as part of the notification. If jinja is required to convert
            # to a string representation it uses str(...) which make it impossible to
            # parse the result as json any longer.
            # TODO: Use to_serializable_dict
            data['result'] = json.dumps(liveaction_db.result)

            payload['message'] = message
            payload['data'] = data
            payload['execution_id'] = execution_id
            payload['status'] = liveaction_db.status
            payload['start_timestamp'] = isotime.format(liveaction_db.start_timestamp)

            try:
                payload['end_timestamp'] = isotime.format(liveaction_db.end_timestamp)
            except AttributeError:
                # This can be raised if liveaction.end_timestamp is None, which is caused
                # when policy cancels a request due to concurrency
                # In this case, use datetime.now() instead
                payload['end_timestamp'] = isotime.format(datetime.utcnow())

            payload['action_ref'] = liveaction_db.action
            payload['runner_ref'] = self._get_runner_ref(liveaction_db.action)

            trace_context = self._get_trace_context(execution_id=execution_id)

            failed_routes = []
            for route in routes:
                try:
                    payload['route'] = route
                    # Deprecated. Only for backward compatibility reasons.
                    payload['channel'] = route
                    LOG.debug('POSTing %s for %s. Payload - %s.', NOTIFY_TRIGGER_TYPE['name'],
                              liveaction_db.id, payload)
                    self._trigger_dispatcher.dispatch(self._notify_trigger, payload=payload,
                                                      trace_context=trace_context)
                except:
                    failed_routes.append(route)

            if len(failed_routes) > 0:
                raise Exception('Failed notifications to routes: %s' % ', '.join(failed_routes))

    def _build_jinja_context(self, liveaction_db, execution_db):
        context = {}
        context.update({
            DATASTORE_PARENT_SCOPE: {
                SYSTEM_SCOPE: KeyValueLookup(scope=FULL_SYSTEM_SCOPE)
            }
        })
        context.update({ACTION_PARAMETERS_KV_PREFIX: liveaction_db.parameters})
        context.update({ACTION_CONTEXT_KV_PREFIX: liveaction_db.context})
        context.update({ACTION_RESULTS_KV_PREFIX: execution_db.result})
        return context

    def _transform_message(self, message, context=None):
        mapping = {'message': message}
        context = context or {}
        return (jinja_utils.render_values(mapping=mapping, context=context)).get('message',
                                                                                 message)

    def _transform_data(self, data, context=None):
        return jinja_utils.render_values(mapping=data, context=context)

    def _get_trace_context(self, execution_id):
        trace_db = trace_service.get_trace_db_by_action_execution(
            action_execution_id=execution_id)
        if trace_db:
            return TraceContext(id_=str(trace_db.id), trace_tag=trace_db.trace_tag)
        # If no trace_context is found then do not create a new one here. If necessary
        # it shall be created downstream. Sure this is impl leakage of some sort.
        return None

    def _post_generic_trigger(self, liveaction_db=None, execution_db=None):
        if not ACTION_SENSOR_ENABLED:
            LOG.debug('Action trigger is disabled, skipping trigger dispatch...')
            return

        execution_id = str(execution_db.id)
        payload = {'execution_id': execution_id,
                   'status': liveaction_db.status,
                   'start_timestamp': str(liveaction_db.start_timestamp),
                   # deprecate 'action_name' at some point and switch to 'action_ref'
                   'action_name': liveaction_db.action,
                   'action_ref': liveaction_db.action,
                   'runner_ref': self._get_runner_ref(liveaction_db.action),
                   'parameters': liveaction_db.get_masked_parameters(),
                   'result': liveaction_db.result}
        # Use execution_id to extract trace rather than liveaction. execution_id
        # will look-up an exact TraceDB while liveaction depending on context
        # may not end up going to the DB.
        trace_context = self._get_trace_context(execution_id=execution_id)
        LOG.debug('POSTing %s for %s. Payload - %s. TraceContext - %s',
                  ACTION_TRIGGER_TYPE['name'], liveaction_db.id, payload, trace_context)
        self._trigger_dispatcher.dispatch(self._action_trigger, payload=payload,
                                          trace_context=trace_context)

    def _apply_post_run_policies(self, liveaction_db):
        # Apply policies defined for the action.
        policy_dbs = Policy.query(resource_ref=liveaction_db.action, enabled=True)
        LOG.debug('Applying %s post_run policies' % (len(policy_dbs)))

        for policy_db in policy_dbs:
            driver = policies.get_driver(policy_db.ref,
                                         policy_db.policy_type,
                                         **policy_db.parameters)

            try:
                LOG.debug('Applying post_run policy "%s" (%s) for liveaction %s' %
                          (policy_db.ref, policy_db.policy_type, str(liveaction_db.id)))
                liveaction_db = driver.apply_after(liveaction_db)
            except:
                LOG.exception('An exception occurred while applying policy "%s".', policy_db.ref)

        return liveaction_db

    def _get_runner_ref(self, action_ref):
        """
        Retrieve a runner reference for the provided action.

        :rtype: ``str``
        """
        action = Action.get_by_ref(action_ref)
        return action['runner_type']['name']


def get_notifier():
    with Connection(transport_utils.get_messaging_urls()) as conn:
        return Notifier(conn, [NOTIFIER_ACTIONUPDATE_WORK_QUEUE],
                        trigger_dispatcher=TriggerDispatcher(LOG))
