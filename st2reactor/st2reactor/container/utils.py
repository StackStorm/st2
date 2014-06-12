import datetime

import st2reactor.ruleenforcement.enforce
from st2common import log as logging
from st2common.persistence.reactor import Trigger, TriggerInstance
from st2common.models.db.reactor import TriggerDB, TriggerInstanceDB


LOG = logging.getLogger('st2reactor.sensor.dispatcher')
DISPATCH_HANDLER = st2reactor.ruleenforcement.enforce.handle_trigger_instances


def __create_trigger_instance(trigger_name, payload,
                              occurrence_time=datetime.datetime.now()):
    triggers = Trigger.query(name=trigger_name)
    trigger = None if len(triggers) == 0 else triggers[0]
    if trigger is None:
        LOG.info('No trigger with name {} found.', trigger_name)
        return None
    trigger_instance = TriggerInstanceDB()
    trigger_instance.name = 'auto-generated'
    trigger_instance.trigger = trigger
    trigger_instance.payload = payload
    trigger_instance.occurrence_time = occurrence_time
    return TriggerInstance.add_or_update(trigger_instance)


def dispatch_triggers(triggers):
    """
    """
    trigger_instances = [__create_trigger_instance(
        trigger['name'],
        trigger['payload'] if 'payload' in trigger else {},
        trigger['occurrence_time'] if 'occurrence_time' in trigger else
        datetime.datetime.now())
        for trigger in triggers]
    DISPATCH_HANDLER(trigger_instances)


def dispatch_trigger(trigger):
    """
    Trigger must have named properties name, payload, occurrence_time.
    """
    dispatch_triggers([trigger])


def __create_trigger_type(name, description=None, payload_info=None):
    triggers = Trigger.query(name=name)
    trigger_type = TriggerDB()
    if len(triggers) > 0:
        trigger_type = triggers[0]
        LOG.info('Found existing trigger id:%s with name:%s. Will update '
                 'trigger.', trigger_type.id, name)
    trigger_type.name = name
    trigger_type.description = description
    trigger_type.payload_info = payload_info
    return Trigger.add_or_update(trigger_type)


def add_trigger_types(trigger_types):
    triggers = [__create_trigger_type(
        trigger_type['name'],
        trigger_type['description'] if 'description' in trigger_type else '',
        trigger_type['payload_info'] if 'payload_info' in trigger_type else [])
        for trigger_type in trigger_types]
    return triggers


def add_trigger_type(trigger_type):
    return add_trigger_types([trigger_type])
