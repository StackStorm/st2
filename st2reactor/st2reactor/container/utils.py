import datetime

from st2common import log as logging
from st2common.exceptions.sensors import TriggerTypeRegistrationException
from st2common.persistence.reactor import Trigger, TriggerInstance
from st2common.models.db.reactor import TriggerDB, TriggerInstanceDB

LOG = logging.getLogger('st2reactor.sensor.container_utils')


def create_trigger_instance(trigger_name, payload,
                            occurrence_time=datetime.datetime.now()):
    triggers = Trigger.query(name=trigger_name)
    trigger = None if len(triggers) == 0 else triggers[0]
    if trigger is None:
        LOG.info('No trigger with name %s found.', trigger_name)
        return None
    trigger_instance = TriggerInstanceDB()
    trigger_instance.name = 'auto-generated'
    trigger_instance.trigger = trigger
    trigger_instance.payload = payload
    trigger_instance.occurrence_time = occurrence_time
    return TriggerInstance.add_or_update(trigger_instance)


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


def __validate_trigger_type(trigger_type):
    """
    XXX: We need validator objects that define the required and optional fields.
    For now, manually check them.
    """
    required_fields = ['name']
    for field in required_fields:
        if field not in trigger_type:
            raise TriggerTypeRegistrationException('Invaid trigger type. Missing field %s' % field)


def __add_trigger_type(trigger_type):
    __create_trigger_type(
        trigger_type['name'],
        trigger_type['description'] if 'description' in trigger_type else '',
        trigger_type['payload_info'] if 'payload_info' in trigger_type else [])


def add_trigger_types(trigger_types):
    [r for r in (__validate_trigger_type(trigger_type)
     for trigger_type in trigger_types) if r is not None]
    return [r for r in (__add_trigger_type(trigger_type)
            for trigger_type in trigger_types) if r is not None]
