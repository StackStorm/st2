from st2common import log as logging
from st2common.exceptions.sensors import TriggerTypeRegistrationException
from st2common.persistence.reactor import TriggerType, Trigger, TriggerInstance
from st2common.models.db.reactor import TriggerTypeDB, TriggerInstanceDB
from st2common.util import reference

LOG = logging.getLogger('st2reactor.sensor.container_utils')


def create_trigger_instance(trigger, payload, occurrence_time):
    trigger_ = Trigger.query(type__name=trigger['type']['name'],
                             parameters=trigger['parameters']).first()
    if trigger_ is None:
        LOG.info('No trigger with name %s and parameters %s found.',
                 trigger['type']['name'], trigger['parameters'])
        return None
    trigger_instance = TriggerInstanceDB()
    trigger_instance.trigger = reference.get_ref_from_model(trigger_)
    trigger_instance.payload = payload
    trigger_instance.occurrence_time = occurrence_time
    return TriggerInstance.add_or_update(trigger_instance)


def __create_trigger_type(name, description=None, payload_schema=None, parameters_schema=None):
    triggertypes = TriggerType.query(name=name)
    if len(triggertypes) > 0:
        trigger_type = triggertypes[0]
        LOG.info('Found existing trigger id:%s with name:%s. Will update '
                 'trigger.', trigger_type.id, name)
    else:
        trigger_type = TriggerTypeDB()
    trigger_type.name = name
    trigger_type.description = description
    trigger_type.payload_schema = payload_schema
    trigger_type.parameters_schema = parameters_schema
    return TriggerType.add_or_update(trigger_type)


def __validate_trigger_type(trigger_type):
    """
    XXX: We need validator objects that define the required and optional fields.
    For now, manually check them.
    """
    required_fields = ['name']
    for field in required_fields:
        if field not in trigger_type:
            raise TriggerTypeRegistrationException('Invalid trigger type. Missing field %s' % field)


def __add_trigger_type(trigger_type):
    __create_trigger_type(
        trigger_type['name'],
        trigger_type['description'] if 'description' in trigger_type else '',
        trigger_type['payload_schema'] if 'payload_schema' in trigger_type else {},
        trigger_type['parameters_schema'] if 'parameters_schema' in trigger_type else {})


def add_trigger_types(trigger_types):
    [r for r in (__validate_trigger_type(trigger_type)
     for trigger_type in trigger_types) if r is not None]
    return [r for r in (__add_trigger_type(trigger_type)
            for trigger_type in trigger_types) if r is not None]
