from st2common import log as logging
from st2common.exceptions.sensors import TriggerTypeRegistrationException
from st2common.persistence.reactor import TriggerType, TriggerInstance
from st2common.models.db.reactor import TriggerTypeDB, TriggerInstanceDB
from st2common.util import reference
from st2reactorcontroller.service import triggers as TriggerService

LOG = logging.getLogger('st2reactor.sensor.container_utils')


def create_trigger_instance(trigger, payload, occurrence_time):
    trigger_db = TriggerService.get_trigger_db(trigger)
    if trigger_db is None:
        LOG.info('No trigger in db for %s', trigger)
        return None
    trigger_instance = TriggerInstanceDB()
    trigger_instance.trigger = reference.get_ref_from_model(trigger_db)
    trigger_instance.payload = payload
    trigger_instance.occurrence_time = occurrence_time
    return TriggerInstance.add_or_update(trigger_instance)


def _create_trigger_type(name, description=None, payload_schema=None, parameters_schema=None):
    triggertypes = TriggerType.query(name=name)
    is_update = False
    if len(triggertypes) > 0:
        trigger_type = triggertypes[0]
        LOG.debug('Found existing trigger id:%s with name:%s. Will update '
                  'trigger.', trigger_type.id, name)
        is_update = True
    else:
        trigger_type = TriggerTypeDB()
    trigger_type.name = name
    trigger_type.description = description
    trigger_type.payload_schema = payload_schema
    trigger_type.parameters_schema = parameters_schema
    triggertype_db = TriggerType.add_or_update(trigger_type)
    if is_update:
        LOG.audit('TriggerType updated. TriggerType=%s', triggertype_db)
    else:
        LOG.audit('TriggerType created. TriggerType=%s', triggertype_db)
    return triggertype_db


def _validate_trigger_type(trigger_type):
    """
    XXX: We need validator objects that define the required and optional fields.
    For now, manually check them.
    """
    required_fields = ['name']
    for field in required_fields:
        if field not in trigger_type:
            raise TriggerTypeRegistrationException('Invalid trigger type. Missing field %s' % field)


def _create_trigger(trigger_type):
    if hasattr(trigger_type, 'parameters_schema') and not trigger_type['parameters_schema']:
        trigger_db = TriggerService.get_trigger_db(trigger_type.name)
        if trigger_db is None:
            trigger_dict = {'name': trigger_type.name, 'type': trigger_type.name}
            trigger_db = TriggerService.create_trigger_db(trigger_dict)
        return trigger_db
    else:
        LOG.debug('Won\'t create Trigger object as TriggerType %s expects ' +
                  'parameters.', trigger_type)
        return None


def _add_trigger_models(trigger_type):
    try:
        trigger_type = _create_trigger_type(
            trigger_type['name'],
            trigger_type['description'] if 'description' in trigger_type else '',
            trigger_type['payload_schema'] if 'payload_schema' in trigger_type else {},
            trigger_type['parameters_schema'] if 'parameters_schema' in trigger_type else {})
    except:
        raise

    else:
        try:
            trigger = _create_trigger(trigger_type)
        except:
            LOG.exception('Unable to create a trigger db object for trigger_type: %s', trigger_type)
            raise
        else:
            return (trigger_type, trigger)


def add_trigger_models(trigger_types):
    [r for r in (_validate_trigger_type(trigger_type)
     for trigger_type in trigger_types) if r is not None]
    return [r for r in (_add_trigger_models(trigger_type)
            for trigger_type in trigger_types) if r is not None]
