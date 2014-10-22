from st2common import log as logging
from st2common.models.api.reactor import TriggerAPI
from st2common.models.system.common import ResourceReference
from st2common.persistence.reactor import Trigger

LOG = logging.getLogger(__name__)


def _get_trigger_db(type=None, parameters=None):
    try:
        return Trigger.query(type=type,
                             parameters=parameters).first()
    except ValueError as e:
        LOG.debug('Database lookup for type="%s" parameters="%s" resulted ' +
                  'in exception : %s.', type, parameters, e, exc_info=True)
        return None


def _get_trigger_db_by_name_and_pack(name, pack):
    try:
        return Trigger.query(name=name, content_pack=pack).first()
    except ValueError as e:
        LOG.debug('Database lookup for name="%s",pack="%s" resulted ' +
                  'in exception : %s.', name, pack, e, exc_info=True)
        return None


def get_trigger_db(trigger):
    # TODO: This method should die in a fire
    if isinstance(trigger, str) or isinstance(trigger, unicode):
        # Assume reference was passed in
        ref_obj = ResourceReference.from_string_reference(ref=trigger)
        return _get_trigger_db_by_name_and_pack(name=ref_obj.name,
                                                pack=ref_obj.pack)
    if isinstance(trigger, dict):
        name = trigger.get('name', None)
        content_pack = trigger.get('content_pack', None)

        if name and content_pack:
            return _get_trigger_db_by_name_and_pack(name=name, pack=content_pack)

        return _get_trigger_db(type=trigger['type'],
                               parameters=trigger.get('parameters', {}))

    if isinstance(trigger, object):
        name = getattr(trigger, 'name', None)
        content_pack = getattr(trigger, 'content_pack', None)
        parameters = getattr(trigger, 'parameters', {})

        trigger_db = None
        if name and content_pack:
            trigger_db = _get_trigger_db_by_name_and_pack(name=name, pack=content_pack)
        else:
            trigger_db = _get_trigger_db(type=trigger.type,
                                         parameters=parameters)
        return trigger_db
    else:
        raise Exception('Unrecognized object')


def _get_trigger_api_given_rule(rule):
    trigger = rule.trigger
    triggertype_ref = ResourceReference.from_string_reference(trigger.get('type'))
    trigger_dict = {}
    trigger_name = trigger.get('name', None)
    if trigger_name:
        trigger_dict['name'] = trigger_name
    trigger_dict['content_pack'] = triggertype_ref.pack
    trigger_dict['type'] = triggertype_ref.ref
    trigger_dict['parameters'] = rule.trigger.get('parameters', {})
    trigger_api = TriggerAPI(**trigger_dict)

    return trigger_api


def create_trigger_db(trigger):
    trigger_api = trigger
    if isinstance(trigger, dict):
        trigger_api = TriggerAPI(**trigger)
    trigger_db = get_trigger_db(trigger_api)
    if not trigger_db:
        trigger_db = TriggerAPI.to_model(trigger_api)
        LOG.debug('verified trigger and formulated TriggerDB=%s', trigger_db)
        trigger_db = Trigger.add_or_update(trigger_db)
    return trigger_db


def create_trigger_db_from_rule(rule):
    trigger_api = _get_trigger_api_given_rule(rule)
    return create_trigger_db(trigger_api)
