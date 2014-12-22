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

from st2common import log as logging
from st2common.models.api.reactor import (TriggerAPI, TriggerTypeAPI)
from st2common.models.system.common import ResourceReference
from st2common.persistence.reactor import (Trigger, TriggerType)

__all__ = [
    'get_trigger_db',
    'get_trigger_type_db',

    'create_trigger_db',
    'create_trigger_type_db',

    'create_or_update_trigger_db',
    'create_or_update_trigger_type_db'
]

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
        return Trigger.query(name=name, pack=pack).first()
    except ValueError as e:
        LOG.debug('Database lookup for name="%s",pack="%s" resulted ' +
                  'in exception : %s.', name, pack, e, exc_info=True)
        return None


def get_trigger_db(trigger):
    # TODO: This method should die in a fire
    if isinstance(trigger, str) or isinstance(trigger, unicode):
        # Assume reference was passed in
        return Trigger.get_by_ref(trigger)
    if isinstance(trigger, dict):
        name = trigger.get('name', None)
        pack = trigger.get('pack', None)

        if name and pack:
            return _get_trigger_db_by_name_and_pack(name=name, pack=pack)

        return _get_trigger_db(type=trigger['type'],
                               parameters=trigger.get('parameters', {}))

    if isinstance(trigger, object):
        name = getattr(trigger, 'name', None)
        pack = getattr(trigger, 'pack', None)
        parameters = getattr(trigger, 'parameters', {})

        trigger_db = None
        if name and pack:
            trigger_db = _get_trigger_db_by_name_and_pack(name=name, pack=pack)
        else:
            trigger_db = _get_trigger_db(type=trigger.type,
                                         parameters=parameters)
        return trigger_db
    else:
        raise Exception('Unrecognized object')


def get_trigger_type_db(ref):
    """
    Returns the trigger type object from db given a string ref.

    :param ref: Reference to the trigger type db object.
    :type ref: ``str``

    :rtype trigger_type: ``object``
    """
    try:
        return TriggerType.get_by_ref(ref)
    except ValueError as e:
        LOG.debug('Database lookup for ref="%s" resulted ' +
                  'in exception : %s.', ref, e, exc_info=True)
        return None


def _get_trigger_api_given_rule(rule):
    trigger = rule.trigger
    triggertype_ref = ResourceReference.from_string_reference(trigger.get('type'))
    trigger_dict = {}
    trigger_name = trigger.get('name', None)
    if trigger_name:
        trigger_dict['name'] = trigger_name
    trigger_dict['pack'] = triggertype_ref.pack
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
        LOG.debug('Verified trigger and formulated TriggerDB=%s', trigger_db)
        trigger_db = Trigger.add_or_update(trigger_db)
    return trigger_db


def create_or_update_trigger_db(trigger):
    """
    Create a new TriggerDB model if one doesn't exist yet or update existing
    one.

    :param trigger: Trigger info.
    :type trigger: ``dict``
    """
    assert isinstance(trigger, dict)

    trigger_api = TriggerAPI(**trigger)
    trigger_api = TriggerAPI.to_model(trigger_api)

    existing_trigger_db = get_trigger_db(trigger_api)

    if existing_trigger_db:
        is_update = True
    else:
        is_update = False

    if is_update:
        trigger_api.id = existing_trigger_db.id

    trigger_db = Trigger.add_or_update(trigger_api)

    if is_update:
        LOG.audit('Trigger updated. Trigger=%s', trigger_db)
    else:
        LOG.audit('Trigger created. Trigger=%s', trigger_db)

    return trigger_db


def create_trigger_db_from_rule(rule):
    trigger_api = _get_trigger_api_given_rule(rule)
    return create_trigger_db(trigger_api)


def create_trigger_type_db(trigger_type):
    """
    Creates a trigger type db object in the db given trigger_type definition as dict.

    :param trigger_type: Trigger type model.
    :type trigger_type: ``dict``

    :rtype: ``object``
    """
    trigger_type_api = TriggerTypeAPI(**trigger_type)
    ref = ResourceReference.to_string_reference(name=trigger_type_api.name,
                                                pack=trigger_type_api.pack)
    trigger_type_db = get_trigger_type_db(ref)

    if not trigger_type_db:
        trigger_type_db = TriggerTypeAPI.to_model(trigger_type_api)
        LOG.debug('verified trigger and formulated TriggerDB=%s', trigger_type_db)
        trigger_type_db = TriggerType.add_or_update(trigger_type_db)
    return trigger_type_db


def create_or_update_trigger_type_db(trigger_type):
    """
    Create or update a trigger type db object in the db given trigger_type definition as dict.

    :param trigger_type: Trigger type model.
    :type trigger_type: ``dict``

    :rtype: ``object``
    """
    assert isinstance(trigger_type, dict)

    trigger_type_api = TriggerTypeAPI(**trigger_type)
    trigger_type_api = TriggerTypeAPI.to_model(trigger_type_api)

    ref = ResourceReference.to_string_reference(name=trigger_type_api.name,
                                                pack=trigger_type_api.pack)

    existing_trigger_type_db = get_trigger_type_db(ref)
    if existing_trigger_type_db:
        is_update = True
    else:
        is_update = False

    if is_update:
        trigger_type_api.id = existing_trigger_type_db.id

    trigger_type_db = TriggerType.add_or_update(trigger_type_api)

    if is_update:
        LOG.audit('TriggerType updated. TriggerType=%s', trigger_type_db)
    else:
        LOG.audit('TriggerType created. TriggerType=%s', trigger_type_db)

    return trigger_type_db
