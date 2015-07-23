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
import st2common.content.utils as content_utils
from st2common.models.api.sensor import SensorInstanceAPI
from st2common.persistence.sensor import SensorInstance

__all__ = [
    'SensorInstancesRegistrar',
    'register_sensor_instances'
]

LOG = logging.getLogger(__name__)

PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)))


class SensorInstancesRegistrar(ResourceRegistrar):
    ALLOWED_EXTENSIONS = [
        '.yaml',
        '.yml'
    ]

    def register_sensor_instances_from_packs(self, base_dirs):
        """
        Discover all the packs in the provided directory and register sensor instances
        from all of the discovered packs.

        :return: Number of sensor instances registered.
        :rtype: ``int``
        """
        # Register packs first
        self.register_packs(base_dirs=base_dirs)

        registered_count = 0
        content = self._pack_loader.get_content(base_dirs=base_dirs,
                                                content_type='sensorinstances')

        for pack, sensor_instances_dir in six.iteritems(content):
            try:
                LOG.debug('Registering sensor instances from pack %s:, dir: %s', pack,
                          sensor_instances_dir)
                sensor_instances = self._get_sensor_instances_from_pack(sensor_instances_dir)
                count = self._register_sensor_instances_from_pack(pack=pack,
                                                                  sensor_instances=sensor_instances)
                registered_count += count
            except Exception as e:
                LOG.exception('Failed registering all sensor instances from pack "%s": %s',
                              sensor_instances_dir, str(e))

        return registered_count

    def register_sensor_instances_from_pack(self, pack_dir):
        """
        Register all the sensor instances from the provided pack.

        :return: Number of sensor instances registered.
        :rtype: ``int``
        """
        pack_dir = pack_dir[:-1] if pack_dir.endswith('/') else pack_dir
        _, pack = os.path.split(pack_dir)
        sensor_instances_dir = self._pack_loader.get_content_from_pack(
            pack_dir=pack_dir, content_type='sensorinstnaces')

        # Register pack first
        self.register_pack(pack_name=pack, pack_dir=pack_dir)

        registered_count = 0
        if not sensor_instances_dir:
            return registered_count

        LOG.debug('Registering sensor instances from pack %s:, dir: %s', pack, sensor_instances_dir)

        try:
            sensor_instances = self._get_sensor_instances_from_pack(
                sensor_instances_dir=sensor_instances_dir)
            registered_count = self._register_sensor_instances_from_pack(
                pack=pack, sensor_instances=sensor_instances)
        except Exception as e:
            LOG.exception('Failed registering all sensor instances from pack "%s": %s',
                          sensor_instances, str(e))

        return registered_count

    def _get_sensor_instances_from_pack(self, sensor_instances_dir):
        return self.get_resources_from_pack(resources_dir=sensor_instances_dir)

    def _register_sensor_instances_from_pack(self, pack, sensor_instances):
        registered_count = 0

        for sensor_instance in sensor_instances:
            try:
                self._register_sensor_instance_from_pack(pack=pack, sensor_instance=sensor_instance)
            except Exception as e:
                LOG.debug('Failed to register sensor instance "%s": %s', sensor_instance, str(e))
            else:
                LOG.debug('Sensor instance "%s" successfully registered', sensor_instance)
                registered_count += 1

        return registered_count

    def _register_sensor_instance_from_pack(self, pack, sensor_instance):
        sensor_instance_metadata_file_path = sensor_instance

        LOG.debug('Loading sensor instance from %s.', sensor_instance_metadata_file_path)
        content = self._meta_loader.load(file_path=sensor_instance_metadata_file_path)

        pack_field = content.get('pack', None)
        if not pack_field:
            content['pack'] = pack
            pack_field = pack
        if pack_field != pack:
            raise Exception('Model is in pack "%s" but field "pack" is different: %s' %
                            (pack, pack_field))

        sensor_instance_api = SensorInstanceAPI(**content)
        sensor_instance_model = SensorInstanceAPI.to_model(sensor_instance_api)

        sensor_instances = SensorInstance.query(pack=sensor_instance_model.pack,
                                                name=sensor_instance_model.name)
        if len(sensor_instances) >= 1:
            sensor_instance = sensor_instances[0]
            LOG.debug('Found existing sensor instance id:%s with name:%s. Will update it.',
                      sensor_instance.id, sensor_instance.name)
            sensor_instance_model.id = sensor_instance.id

        # TODO: validate SensorInstance.type and parameters.

        try:
            sensor_instance_model = SensorInstance.add_or_update(sensor_instance_model)
        except:
            LOG.exception('Failed creating sensor instance model for %s', sensor_instance)

        return sensor_instance_model


def register_sensor_instances(packs_base_paths=None, pack_dir=None):
    if packs_base_paths:
        assert(isinstance(packs_base_paths, list))

    if not packs_base_paths:
        packs_base_paths = content_utils.get_packs_base_paths()

    registrar = SensorInstancesRegistrar()

    if pack_dir:
        result = registrar.register_sensor_instances_from_pack(pack_dir=pack_dir)
    else:
        result = registrar.register_sensor_instances_from_packs(base_dirs=packs_base_paths)

    return result
