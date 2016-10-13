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

from st2common.constants.pack import SYSTEM_PACK_NAME
from st2common.constants.sensors import MINIMUM_POLL_INTERVAL
from st2common.models.db.sensor import SensorTypeDB
from st2common.services import triggers as trigger_service

__all__ = [
    'to_sensor_db_model',
    'get_sensor_entry_point',
    'create_trigger_types'
]


def to_sensor_db_model(sensor_api_model=None):
    """
    Converts a SensorTypeAPI model to DB model.
    Also, creates trigger type objects provided in SensorTypeAPI.

    :param sensor_api_model: SensorTypeAPI object.
    :type sensor_api_model: :class:`SensorTypeAPI`

    :rtype: :class:`SensorTypeDB`
    """
    class_name = getattr(sensor_api_model, 'class_name', None)
    pack = getattr(sensor_api_model, 'pack', None)
    entry_point = get_sensor_entry_point(sensor_api_model)
    artifact_uri = getattr(sensor_api_model, 'artifact_uri', None)
    description = getattr(sensor_api_model, 'description', None)
    trigger_types = getattr(sensor_api_model, 'trigger_types', [])
    poll_interval = getattr(sensor_api_model, 'poll_interval', None)
    enabled = getattr(sensor_api_model, 'enabled', True)

    poll_interval = getattr(sensor_api_model, 'poll_interval', None)
    if poll_interval and (poll_interval < MINIMUM_POLL_INTERVAL):
        raise ValueError('Minimum possible poll_interval is %s seconds' %
                         (MINIMUM_POLL_INTERVAL))

    # Add pack to each trigger type item
    for trigger_type in trigger_types:
        trigger_type['pack'] = pack
    trigger_type_refs = create_trigger_types(trigger_types)

    return _create_sensor_type(pack=pack,
                               name=class_name,
                               description=description,
                               artifact_uri=artifact_uri,
                               entry_point=entry_point,
                               trigger_types=trigger_type_refs,
                               poll_interval=poll_interval,
                               enabled=enabled)


def create_trigger_types(trigger_types):
    if not trigger_types:
        return []

    # Add TrigerType models to the DB
    trigger_type_dbs = trigger_service.add_trigger_models(trigger_types=trigger_types)

    trigger_type_refs = []
    # Populate a list of references belonging to this sensor
    for trigger_type_db, _ in trigger_type_dbs:
        ref_obj = trigger_type_db.get_reference()
        trigger_type_ref = ref_obj.ref
        trigger_type_refs.append(trigger_type_ref)
    return trigger_type_refs


def _create_sensor_type(pack=None, name=None, description=None, artifact_uri=None,
                        entry_point=None, trigger_types=None, poll_interval=10, enabled=True):

    sensor_type = SensorTypeDB(pack=pack, name=name, description=description,
                               artifact_uri=artifact_uri, entry_point=entry_point,
                               poll_interval=poll_interval, enabled=enabled,
                               trigger_types=trigger_types)
    return sensor_type


def get_sensor_entry_point(sensor_api_model):
    file_path = getattr(sensor_api_model, 'artifact_uri', None)
    class_name = getattr(sensor_api_model, 'class_name', None)
    pack = getattr(sensor_api_model, 'pack', None)

    if pack == SYSTEM_PACK_NAME:
        # Special case for sensors which come included with the default installation
        entry_point = class_name
    else:
        module_path = file_path.split('/%s/' % (pack))[1]
        module_path = module_path.replace(os.path.sep, '.')
        module_path = module_path.replace('.py', '')
        entry_point = '%s.%s' % (module_path, class_name)

    return entry_point
