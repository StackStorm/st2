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
    :param trigger: Dictionary with trigger query filters.
    :type trigger: ``dict``

    :param payload: Trigger payload.
    :type payload: ``dict``
    """
    # TODO: This is nasty, this should take a unique reference and not a dict
    trigger_db = TriggerService.get_trigger_db(trigger)
    if trigger_db is None:
        LOG.info('No trigger in db for %s', trigger)
        return None

    trigger_ref = trigger_db.get_reference().ref

    trigger_instance = TriggerInstanceDB()
    trigger_instance.trigger = trigger_ref
    trigger_instance.payload = payload
    trigger_instance.occurrence_time = occurrence_time
    return TriggerInstance.add_or_update(trigger_instance)


def _create_trigger_type(trigger_type):
    return TriggerService.create_trigger_type_db(trigger_type)


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
        trigger_dict = {
            'name': trigger_type.name,
            'pack': trigger_type.pack,
            'type': trigger_type.get_reference().ref
        }
        return TriggerService.create_trigger_db(trigger_dict)
    else:
        LOG.debug('Won\'t create Trigger object as TriggerType %s expects ' +
                  'parameters.', trigger_type)
        return None


def _add_trigger_models(trigger_type):
    trigger_type = _create_trigger_type(trigger_type)
    trigger = _create_trigger(trigger_type=trigger_type)
    return (trigger_type, trigger)


def add_trigger_models(trigger_types):
    """
    Register trigger types.

    :param trigger_types: A list of triggers to register.
    :type trigger_types: ``list`` of trigger_type.
    """
    [r for r in (_validate_trigger_type(trigger_type)
     for trigger_type in trigger_types) if r is not None]

    result = []
    for trigger_type in trigger_types:
        item = _add_trigger_models(trigger_type=trigger_type)

        if item:
            result.append(item)

    return result


def _create_sensor_type(pack, name, description, artifact_uri, entry_point,
                        trigger_types=None, poll_interval=10):
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
    sensor_type.trigger_types = trigger_types
    sensor_type.poll_interval = poll_interval

    sensor_type_db = SensorType.add_or_update(sensor_type)

    if is_update:
        LOG.audit('SensorType updated. SensorType=%s', sensor_type_db)
    else:
        LOG.audit('SensorType created. SensorType=%s', sensor_type_db)
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

    obj = _create_sensor_type(pack=pack,
                              name=name,
                              description=description,
                              artifact_uri=artifact_uri,
                              entry_point=entry_point,
                              trigger_types=trigger_types,
                              poll_interval=poll_interval)
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
