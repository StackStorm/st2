import datetime
import logging
import st2reactor.ruleenforcement.enforce

from st2common.persistence.reactor import Trigger, TriggerInstance
from st2common.models.db.reactor import TriggerInstanceDB

LOG = logging.getLogger('st2reactor.adapter.dispatcher')
DISPATCH_HANDLER = st2reactor.ruleenforcement.enforce.handle_trigger_instances


def __create_trigger_instance(trigger_id, payload,
                              occurrence_time=datetime.datetime.now()):
    trigger = Trigger.get_by_id(trigger_id)
    trigger_instance = TriggerInstanceDB()
    trigger_instance.trigger = trigger
    trigger_instance.payload = payload
    trigger_instance.occurrence_time = occurrence_time
    TriggerInstance.add_or_update(trigger_instance)
    return trigger_instance


def dispatch_triggers(triggers):
    """
    """
    trigger_instances = [__create_trigger_instance(trigger.trigger_id,
                                                   trigger.payload,
                                                   trigger.occurrence_time)
                         for trigger in triggers]
    DISPATCH_HANDLER(trigger_instances)


def dispatch_trigger(trigger):
    """
    Trigger must have named properties trigger_id, payload, occurence_time.
    """
    dispatch_triggers([trigger])
