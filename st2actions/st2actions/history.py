from kombu import Connection
from kombu.mixins import ConsumerMixin
from oslo.config import cfg

from st2common.util import reference
from st2common.transport import actionexecution, publishers
from st2common.persistence.history import ActionExecutionHistory
from st2common.persistence.action import RunnerType, Action, ActionExecution
from st2common.persistence.reactor import TriggerType, Trigger, TriggerInstance, Rule
from st2common.models.api.action import RunnerTypeAPI, ActionAPI, ActionExecutionAPI
from st2common.models.api.reactor import TriggerTypeAPI, TriggerAPI, TriggerInstanceAPI, RuleAPI
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

    def shutdown(self):
        pass

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
            self.record_action_execution(body)
        except:
            LOG.exception('An unexpected error occurred while recording the action execution.')
        finally:
            message.ack()

    def record_action_execution(self, body):
        execution = ActionExecution.get_by_id(str(body.id))
        history = ActionExecutionHistory.get(execution__id=str(body.id))
        if history:
            history.execution = vars(ActionExecutionAPI.from_model(execution))
        else:
            action = Action.get_by_name(execution.action['name'])
            runner = RunnerType.get_by_name(action.runner_type['name'])
            history = ActionExecutionHistoryDB(
                action=vars(ActionAPI.from_model(action)),
                runner=vars(RunnerTypeAPI.from_model(runner)),
                execution=vars(ActionExecutionAPI.from_model(execution)))
            history = ActionExecutionHistory.add_or_update(history)

        if 'rule' in execution.context:
            rule = reference.get_model_from_ref(Rule, execution.context.get('rule', {}))
            history.rule = vars(RuleAPI.from_model(rule))

        if 'trigger_instance' in execution.context:
            trigger_instance = reference.get_model_from_ref(
                TriggerInstance, execution.context.get('trigger_instance', {}))
            trigger = Trigger.get_by_name(trigger_instance.trigger['name'])
            trigger_type = TriggerType.get_by_name(trigger.type['name'])
            history.trigger_instance = vars(TriggerInstanceAPI.from_model(trigger_instance))
            history.trigger = vars(TriggerAPI.from_model(trigger))
            history.trigger_type = vars(TriggerTypeAPI.from_model(trigger_type))

        parent = ActionExecutionHistory.get(execution__id=execution.context.get('parent', ''))
        if parent:
            history.parent = str(parent.id)
            if str(history.id) not in parent.children:
                parent.children.append(str(history.id))
                ActionExecutionHistory.add_or_update(parent)

        history = ActionExecutionHistory.add_or_update(history)


def work():
    with Connection(cfg.CONF.messaging.url) as conn:
        worker = Historian(conn)
        try:
            worker.run()
        except:
            raise
        finally:
            worker.shutdown()
