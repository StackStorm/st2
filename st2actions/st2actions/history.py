from kombu import Connection
from kombu.mixins import ConsumerMixin
from oslo.config import cfg

from st2common.util import reference
import st2common.util.action_db as action_utils
from st2common.transport import actionexecution, publishers
from st2common.util.greenpooldispatch import BufferedDispatcher
from st2common.persistence.history import ActionExecutionHistory
from st2common.persistence.action import RunnerType, ActionExecution
from st2common.persistence.reactor import TriggerType, Trigger, TriggerInstance, Rule
from st2common.models.api.action import RunnerTypeAPI, ActionAPI, ActionExecutionAPI
from st2common.models.api.reactor import TriggerTypeAPI, TriggerAPI, TriggerInstanceAPI, RuleAPI
from st2common.models.system.common import ResourceReference
from st2common.models.db.history import ActionExecutionHistoryDB
from st2common import log as logging


LOG = logging.getLogger(__name__)

QUEUES = {
    'create': actionexecution.get_queue('st2.hist.exec', routing_key=publishers.CREATE_RK),
    'update': actionexecution.get_queue('st2.hist.exec', routing_key=publishers.UPDATE_RK)
}


class Historian(ConsumerMixin):

    def __init__(self, connection):
        self.connection = connection
        self._dispatcher = BufferedDispatcher()

    def shutdown(self):
        self._dispatcher.shutdown()

    def get_consumers(self, Consumer, channel):
        consumers = [Consumer(queues=QUEUES.values(), accept=['pickle'],
                              callbacks=[self.process_action_execution])]

        # use prefetch_count=1 for fair dispatch. This way workers that finish an item get the next
        # task and the work does not get queued behind any single large item.
        for consumer in consumers:
            consumer.qos(prefetch_count=1)

        return consumers

    def process_action_execution(self, body, message):
        try:
            self._dispatcher.dispatch(self.record_action_execution, body)
        finally:
            message.ack()

    def record_action_execution(self, body):
        try:
            execution = ActionExecution.get_by_id(str(body.id))
            history = ActionExecutionHistory.get(execution__id=str(body.id))
            if history:
                history.execution = vars(ActionExecutionAPI.from_model(execution))
            else:
                action_ref = ResourceReference.from_string_reference(ref=execution.ref)
                action_db, _ = action_utils.get_action_by_dict(
                    {'name': action_ref.name,
                     'content_pack': action_ref.pack})
                runner = RunnerType.get_by_name(action_db.runner_type['name'])
                history = ActionExecutionHistoryDB(
                    action=vars(ActionAPI.from_model(action_db)),
                    runner=vars(RunnerTypeAPI.from_model(runner)),
                    execution=vars(ActionExecutionAPI.from_model(execution)))
                history = ActionExecutionHistory.add_or_update(history)

            if 'rule' in execution.context and not getattr(history, 'rule', None):
                rule = reference.get_model_from_ref(Rule, execution.context.get('rule', {}))
                history.rule = vars(RuleAPI.from_model(rule))

            if ('trigger_instance' in execution.context and
                    not getattr(history, 'trigger_instance', None)):
                trigger_instance = reference.get_model_from_ref(
                    TriggerInstance, execution.context.get('trigger_instance', {}))
                trigger = Trigger.get_by_name(trigger_instance.trigger['name'])
                trigger_type = TriggerType.get_by_name(trigger.type['name'])
                history.trigger_instance = vars(TriggerInstanceAPI.from_model(trigger_instance))
                history.trigger = vars(TriggerAPI.from_model(trigger))
                history.trigger_type = vars(TriggerTypeAPI.from_model(trigger_type))

            parent = ActionExecutionHistory.get(execution__id=execution.context.get('parent', ''))
            if parent and not getattr(history, 'parent', None):
                history.parent = str(parent.id)
                if str(history.id) not in parent.children:
                    parent.children.append(str(history.id))
                    ActionExecutionHistory.add_or_update(parent)

            history = ActionExecutionHistory.add_or_update(history)
        except:
            LOG.exception('An unexpected error occurred while recording the action execution.')


def work():
    with Connection(cfg.CONF.messaging.url) as conn:
        worker = Historian(conn)
        try:
            worker.run()
        except:
            raise
        finally:
            worker.shutdown()
