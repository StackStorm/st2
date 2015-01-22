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

from st2common.util import reference
import st2common.util.action_db as action_utils
from st2common.transport import liveaction, publishers
from st2common.util.greenpooldispatch import BufferedDispatcher
from st2common.persistence.history import ActionExecutionHistory
from st2common.persistence.action import RunnerType, LiveAction
from st2common.persistence.reactor import TriggerType, Trigger, TriggerInstance, Rule
from st2common.models.api.action import RunnerTypeAPI, ActionAPI, LiveActionAPI
from st2common.models.api.reactor import TriggerTypeAPI, TriggerAPI, TriggerInstanceAPI
from st2common.models.api.rule import RuleAPI
from st2common.models.db.history import ActionExecutionHistoryDB
from st2common import log as logging


LOG = logging.getLogger(__name__)

QUEUES = {
    'create': liveaction.get_queue('st2.hist.exec.create', routing_key=publishers.CREATE_RK),
    'update': liveaction.get_queue('st2.hist.exec.update', routing_key=publishers.UPDATE_RK)
}


class Historian(ConsumerMixin):

    def __init__(self, connection, timeout=60, wait=3):
        self.wait = wait
        self.timeout = timeout
        self.connection = connection
        self._dispatcher = BufferedDispatcher()

    def shutdown(self):
        self._dispatcher.shutdown()

    def get_consumers(self, Consumer, channel):
        return [Consumer(queues=[QUEUES['create']], accept=['pickle'],
                         callbacks=[self.process_create]),
                Consumer(queues=[QUEUES['update']], accept=['pickle'],
                         callbacks=[self.process_update])]

    def process_create(self, body, message):
        try:
            self._dispatcher.dispatch(self.record_action_execution, body)
        finally:
            message.ack()

    def process_update(self, body, message):
        try:
            self._dispatcher.dispatch(self.update_action_execution_history, body)
        finally:
            message.ack()

    def record_action_execution(self, body):
        try:
            execution = LiveAction.get_by_id(str(body.id))
            action_db = action_utils.get_action_by_ref(execution.action)
            runner = RunnerType.get_by_name(action_db.runner_type['name'])

            attrs = {
                'action': vars(ActionAPI.from_model(action_db)),
                'runner': vars(RunnerTypeAPI.from_model(runner)),
                'execution': vars(LiveActionAPI.from_model(execution))
            }

            if 'rule' in execution.context:
                rule = reference.get_model_from_ref(Rule, execution.context.get('rule', {}))
                attrs['rule'] = vars(RuleAPI.from_model(rule))

            if 'trigger_instance' in execution.context:
                trigger_instance_id = execution.context.get('trigger_instance', {})
                trigger_instance_id = trigger_instance_id.get('id', None)
                trigger_instance = TriggerInstance.get_by_id(trigger_instance_id)
                trigger = reference.get_model_by_resource_ref(db_api=Trigger,
                                                              ref=trigger_instance.trigger)
                trigger_type = reference.get_model_by_resource_ref(db_api=TriggerType,
                                                                   ref=trigger.type)
                trigger_instance = reference.get_model_from_ref(
                    TriggerInstance, execution.context.get('trigger_instance', {}))
                attrs['trigger_instance'] = vars(TriggerInstanceAPI.from_model(trigger_instance))
                attrs['trigger'] = vars(TriggerAPI.from_model(trigger))
                attrs['trigger_type'] = vars(TriggerTypeAPI.from_model(trigger_type))

            parent = ActionExecutionHistory.get(execution__id=execution.context.get('parent', ''))
            if parent:
                attrs['parent'] = str(parent.id)

            history = ActionExecutionHistoryDB(**attrs)
            history = ActionExecutionHistory.add_or_update(history)

            if parent:
                if str(history.id) not in parent.children:
                    parent.children.append(str(history.id))
                    ActionExecutionHistory.add_or_update(parent)
        except:
            LOG.exception('An unexpected error occurred while creating the '
                          'action execution history.')
            raise

    def update_action_execution_history(self, body):
        try:
            count = self.timeout / self.wait
            # Allow up to 1 minute for the post event to create the history record.
            for i in range(count):
                history = ActionExecutionHistory.get(execution__id=str(body.id))
                if history:
                    execution = LiveAction.get_by_id(str(body.id))
                    history.execution = vars(LiveActionAPI.from_model(execution))
                    history = ActionExecutionHistory.add_or_update(history)
                    return
                if i >= count:
                    # If wait failed, create the history record regardless.
                    self.record_action_execution(body)
                    return
                eventlet.sleep(self.wait)
        except:
            LOG.exception('An unexpected error occurred while updating the '
                          'action execution history.')
            raise


def work():
    with Connection(cfg.CONF.messaging.url) as conn:
        worker = Historian(conn)
        try:
            worker.run()
        except:
            raise
        finally:
            worker.shutdown()
