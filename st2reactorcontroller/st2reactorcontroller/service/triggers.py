from st2common import log as logging
from st2common.models.api.reactor import TriggerAPI
from st2common.persistence.reactor import Trigger

LOG = logging.getLogger(__name__)


def get_trigger_db(trigger):
    trigger_db = None
    if type(trigger) == str:
        trigger = {}
        trigger['name'] = trigger
    if hasattr(trigger, 'name') and trigger.name:
        # If there is a name do a lookup by name first.
        try:
            trigger_db = Trigger.get_by_name(trigger.name)
            LOG.debug('Found matching TriggerDB=%s for trigger=%s', trigger_db, trigger)
        except ValueError as e:
            # It is ok to proceed.
            LOG.debug('Database lookup for name="%s" resulted in exception : %s.', trigger.name, e)
    else:
        trigger_db = Trigger.query(type__name=trigger.type,
                                   parameters=trigger.parameters).first()
        if trigger_db:
            LOG.debug('Found matching TriggerDB=%s for trigger=%s', trigger_db, trigger)
    return trigger_db


def create_trigger_db(trigger):
    trigger_db = get_trigger_db(trigger)
    if not trigger_db:
        trigger_db = TriggerAPI.to_model(trigger)
        LOG.debug('verified trigger and formulated TriggerDB=%s', trigger_db)
        trigger_db = Trigger.add_or_update(trigger_db)
    return trigger_db
