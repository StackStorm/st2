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
from st2common.bootstrap.base import ResourceRegistrar
import st2reactor.container.utils as container_utils
import st2common.content.utils as content_utils

__all__ = [
    'SensorsRegistrar',
    'register_sensors'
]

LOG = logging.getLogger(__name__)

PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)))


class SensorsRegistrar(ResourceRegistrar):
    ALLOWED_EXTENSIONS = [
        '.yaml',
        '.yml'
    ]

    def register_sensors_from_packs(self, base_dirs):
        """
        Discover all the packs in the provided directory and register sensors from all of the
        discovered packs.

        :return: Number of sensors registered.
        :rtype: ``int``
        """
        registered_count = 0

        content = self._pack_loader.get_content(base_dirs=base_dirs,
                                                content_type='sensors')

        for pack, sensors_dir in six.iteritems(content):
            try:
                LOG.debug('Registering sensors from pack %s:, dir: %s', pack, sensors_dir)
                sensors = self._get_sensors_from_pack(sensors_dir)
                count = self._register_sensors_from_pack(pack=pack, sensors=sensors)
                registered_count += count
            except Exception as e:
                LOG.exception('Failed registering all sensors from pack "%s": %s', sensors_dir,
                              str(e))

        return registered_count

    def register_sensors_from_pack(self, pack_dir):
        """
        Register all the sensors from the provided pack.

        :return: Number of sensors registered.
        :rtype: ``int``
        """
        pack_dir = pack_dir[:-1] if pack_dir.endswith('/') else pack_dir
        _, pack = os.path.split(pack_dir)
        sensors_dir = self._pack_loader.get_content_from_pack(pack_dir=pack_dir,
                                                              content_type='sensors')

        registered_count = 0
        if not sensors_dir:
            return registered_count

        LOG.debug('Registering sensors from pack %s:, dir: %s', pack, sensors_dir)

        try:
            sensors = self._get_sensors_from_pack(sensors_dir=sensors_dir)
            registered_count = self._register_sensors_from_pack(pack=pack, sensors=sensors)
        except Exception as e:
            LOG.exception('Failed registering all sensors from pack "%s": %s', sensors_dir, str(e))

        return registered_count

    def _get_sensors_from_pack(self, sensors_dir):
        return self.get_resources_from_pack(resources_dir=sensors_dir)

    def _register_sensors_from_pack(self, pack, sensors):
        registered_count = 0

        for sensor in sensors:
            try:
                self._register_sensor_from_pack(pack=pack, sensor=sensor)
            except Exception as e:
                LOG.debug('Failed to register sensor "%s": %s', sensor, str(e))
            else:
                LOG.debug('Sensor "%s" successfully registered', sensor)
                registered_count += 1

        return registered_count

    def _register_sensor_from_pack(self, pack, sensor):
        sensor_metadata_file_path = sensor

        LOG.debug('Loading sensor from %s.', sensor_metadata_file_path)
        metadata = self._meta_loader.load(file_path=sensor_metadata_file_path)

        class_name = metadata.get('class_name', None)
        entry_point = metadata.get('entry_point', None)
        description = metadata.get('description', None)
        trigger_types = metadata.get('trigger_types', [])
        poll_interval = metadata.get('poll_interval', None)
        enabled = metadata.get('enabled', True)

        # Add pack to each trigger type item
        for trigger_type in trigger_types:
            trigger_type['pack'] = pack

        # Add TrigerType models to the DB
        trigger_type_dbs = container_utils.add_trigger_models(trigger_types=trigger_types)

        # Populate a list of references belonging to this sensor
        trigger_type_refs = []
        for trigger_type_db, _ in trigger_type_dbs:
            ref_obj = trigger_type_db.get_reference()
            trigger_type_ref = ref_obj.ref
            trigger_type_refs.append(trigger_type_ref)

        if entry_point and class_name:
            sensors_dir = os.path.dirname(sensor_metadata_file_path)
            sensor_file_path = os.path.join(sensors_dir, entry_point)
            # Add Sensor model to the DB
            sensor_obj = {
                'name': class_name,
                'description': description,
                'class_name': class_name,
                'file_path': sensor_file_path,
                'trigger_types': trigger_type_refs,
                'poll_interval': poll_interval,
                'enabled': enabled
            }
            container_utils.add_sensor_model(pack=pack, sensor=sensor_obj)


def register_sensors(packs_base_paths=None, pack_dir=None):
    if packs_base_paths:
        assert(isinstance(packs_base_paths, list))

    if not packs_base_paths:
        packs_base_paths = content_utils.get_packs_base_paths()

    registrar = SensorsRegistrar()

    if pack_dir:
        result = registrar.register_sensors_from_pack(pack_dir=pack_dir)
    else:
        result = registrar.register_sensors_from_packs(base_dirs=packs_base_paths)

    return result
