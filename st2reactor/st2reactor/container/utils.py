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

import os

import six

from st2common import log as logging
from st2common.exceptions.sensors import TriggerTypeRegistrationException
from st2common.persistence.reactor import SensorType, TriggerInstance
from st2common.models.db.reactor import SensorTypeDB, TriggerInstanceDB
from st2common.services import triggers as TriggerService
from st2common.constants.pack import SYSTEM_PACK_NAME
from st2common.constants.sensors import MINIMUM_POLL_INTERVAL

LOG = logging.getLogger('st2reactor.sensor.container_utils')


def create_trigger_instance(trigger, payload, occurrence_time):
    """
    This creates a trigger instance object given trigger and payload.
    Trigger can be just a string reference (pack.name) or a ``dict``
    containing  'type' and 'parameters'.

    :param trigger: Dictionary with trigger query filters.
    :type trigger: ``dict``

    :param payload: Trigger payload.
    :type payload: ``dict``
    """
    # TODO: This is nasty, this should take a unique reference and not a dict
    if isinstance(trigger, six.string_types):
        trigger_db = TriggerService.get_trigger_db_by_ref(trigger)
    else:
        type = trigger.get('type', None)
        parameters = trigger.get('parameters', {})
        trigger_db = TriggerService.get_trigger_db_given_type_and_params(type=type,
                                                                         parameters=parameters)

    if trigger_db is None:
        LOG.info('No trigger in db for %s', trigger)
        return None

    trigger_ref = trigger_db.get_reference().ref

    trigger_instance = TriggerInstanceDB()
    trigger_instance.trigger = trigger_ref
    trigger_instance.payload = payload
    trigger_instance.occurrence_time = occurrence_time
    return TriggerInstance.add_or_update(trigger_instance)


def _create_trigger_type(pack, name, description=None, payload_schema=None,
                         parameters_schema=None):
    trigger_type = {
        'name': name,
        'pack': pack,
        'description': description,
        'payload_schema': payload_schema,
        'parameters_schema': parameters_schema
    }

    trigger_type_db = TriggerService.create_or_update_trigger_type_db(trigger_type=trigger_type)
    return trigger_type_db


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
    """
    :param trigger_type: TriggerType db object.
    :type trigger_type: :class:`TriggerTypeDB`
    """
    if hasattr(trigger_type, 'parameters_schema') and not trigger_type['parameters_schema']:
        trigger_dict = {
            'name': trigger_type.name,
            'pack': trigger_type.pack,
            'type': trigger_type.get_reference().ref
        }

        try:
            trigger_db = TriggerService.create_or_update_trigger_db(trigger=trigger_dict)
        except:
            LOG.exception('Validation failed for Trigger=%s.', trigger_dict)
            raise TriggerTypeRegistrationException(
                'Unable to create Trigger for TriggerType=%s.' % trigger_type.name)
        else:
            return trigger_db
    else:
        LOG.debug('Won\'t create Trigger object as TriggerType %s expects ' +
                  'parameters.', trigger_type)
        return None


def _add_trigger_models(trigger_type):
    pack = trigger_type['pack']
    description = trigger_type['description'] if 'description' in trigger_type else ''
    payload_schema = trigger_type['payload_schema'] if 'payload_schema' in trigger_type else {}
    parameters_schema = trigger_type['parameters_schema'] \
        if 'parameters_schema' in trigger_type else {}

    trigger_type = _create_trigger_type(
        pack=pack,
        name=trigger_type['name'],
        description=description,
        payload_schema=payload_schema,
        parameters_schema=parameters_schema
    )
    trigger = _create_trigger(trigger_type=trigger_type)
    return (trigger_type, trigger)


def add_trigger_models(trigger_types):
    """
    Register trigger types.

    :param trigger_types: A list of triggers to register.
    :type trigger_types: ``list`` of ``dict``

    :rtype: ``list`` of ``tuple`` (trigger_type, trigger)
    """
    [r for r in (_validate_trigger_type(trigger_type)
     for trigger_type in trigger_types) if r is not None]

    result = []
    for trigger_type in trigger_types:
        item = _add_trigger_models(trigger_type=trigger_type)

        if item:
            result.append(item)

    return result


def _create_sensor_type(pack, name, description, artifact_uri, entry_point, file_uri,
                        trigger_types=None, poll_interval=10, enabled=True):
    sensor_types = SensorType.query(pack=pack, name=name)
    is_update = False

    if poll_interval and (poll_interval < MINIMUM_POLL_INTERVAL):
        raise ValueError('Minimum possible poll_interval is %s seconds' %
                         (MINIMUM_POLL_INTERVAL))

    if len(sensor_types) >= 1:
        sensor_type = sensor_types[0]
        LOG.debug('Found existing sensor id:%s with name:%s. Will update it.',
                  sensor_type.id, name)
        is_update = True
    else:
        sensor_type = SensorTypeDB()

    sensor_type.pack = pack
    sensor_type.name = name
    sensor_type.description = description
    sensor_type.artifact_uri = artifact_uri
    sensor_type.entry_point = entry_point
    sensor_type.file_uri = file_uri
    sensor_type.trigger_types = trigger_types
    sensor_type.poll_interval = poll_interval
    sensor_type.enabled = enabled

    sensor_type_db = SensorType.add_or_update(sensor_type)

    extra = {'sensor_type_db': sensor_type_db}
    if is_update:
        LOG.audit('SensorType updated. SensorType.id=%s' % (sensor_type_db.id), extra=extra)
    else:
        LOG.audit('SensorType created. SensorType.id=%s' % (sensor_type_db.id), extra=extra)
    return sensor_type_db


def get_sensor_entry_point(pack, sensor):
    file_path = sensor['file_path']
    class_name = sensor['class_name']

    if pack == SYSTEM_PACK_NAME:
        # Special case for sensors which come included with the default installation
        entry_point = class_name
    else:
        module_path = file_path.split('/%s/' % (pack))[1]
        module_path = module_path.replace(os.path.sep, '.')
        module_path = module_path.replace('.py', '')
        entry_point = '%s.%s' % (module_path, class_name)

    return entry_point


def _add_sensor_model(pack, sensor):
    name = sensor['name']
    description = sensor['description']
    file_path = sensor['file_path']
    artifact_uri = 'file://%s' % (file_path)
    entry_point = get_sensor_entry_point(pack=pack, sensor=sensor)
    trigger_types = sensor['trigger_types'] or []
    poll_interval = sensor['poll_interval']
    enabled = sensor['enabled']
    file_uri = sensor['file_uri']

    obj = _create_sensor_type(pack=pack,
                              name=name,
                              description=description,
                              artifact_uri=artifact_uri,
                              entry_point=entry_point,
                              file_uri=file_uri,
                              trigger_types=trigger_types,
                              poll_interval=poll_interval,
                              enabled=enabled)
    return obj


def add_sensor_model(pack, sensor):
    """
    Register sensor type.

    :param pack: Content pack the sensor belongs to.
    :type pack: ``str``

    :param sensor: Sensors to register.
    :type sensor: ``dict``

    :return: DB object of a registered sensor.
    """

    item = _add_sensor_model(pack=pack,
                             sensor=sensor)
    return item
