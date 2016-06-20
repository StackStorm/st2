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
from st2common.constants.meta import ALLOWED_EXTS
from st2common.bootstrap.base import ResourceRegistrar
import st2common.content.utils as content_utils
from st2common.models.api.sensor import SensorTypeAPI
from st2common.persistence.sensor import SensorType

__all__ = [
    'SensorsRegistrar',
    'register_sensors'
]

LOG = logging.getLogger(__name__)

PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)))


class SensorsRegistrar(ResourceRegistrar):
    ALLOWED_EXTENSIONS = ALLOWED_EXTS

    def register_sensors_from_packs(self, base_dirs):
        """
        Discover all the packs in the provided directory and register sensors from all of the
        discovered packs.

        :return: Number of sensors registered.
        :rtype: ``int``
        """
        # Register packs first
        self.register_packs(base_dirs=base_dirs)

        registered_count = 0
        content = self._pack_loader.get_content(base_dirs=base_dirs,
                                                content_type='sensors')

        for pack, sensors_dir in six.iteritems(content):
            if not sensors_dir:
                LOG.debug('Pack %s does not contain sensors.', pack)
                continue
            try:
                LOG.debug('Registering sensors from pack %s:, dir: %s', pack, sensors_dir)
                sensors = self._get_sensors_from_pack(sensors_dir)
                count = self._register_sensors_from_pack(pack=pack, sensors=sensors)
                registered_count += count
            except Exception as e:
                if self._fail_on_failure:
                    raise e

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

        # Register pack first
        self.register_pack(pack_name=pack, pack_dir=pack_dir)

        registered_count = 0
        if not sensors_dir:
            return registered_count

        LOG.debug('Registering sensors from pack %s:, dir: %s', pack, sensors_dir)

        try:
            sensors = self._get_sensors_from_pack(sensors_dir=sensors_dir)
            registered_count = self._register_sensors_from_pack(pack=pack, sensors=sensors)
        except Exception as e:
            if self._fail_on_failure:
                raise e

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
                if self._fail_on_failure:
                    raise e

                LOG.debug('Failed to register sensor "%s": %s', sensor, str(e))
            else:
                LOG.debug('Sensor "%s" successfully registered', sensor)
                registered_count += 1

        return registered_count

    def _register_sensor_from_pack(self, pack, sensor):
        sensor_metadata_file_path = sensor

        LOG.debug('Loading sensor from %s.', sensor_metadata_file_path)
        content = self._meta_loader.load(file_path=sensor_metadata_file_path)

        pack_field = content.get('pack', None)
        if not pack_field:
            content['pack'] = pack
            pack_field = pack
        if pack_field != pack:
            raise Exception('Model is in pack "%s" but field "pack" is different: %s' %
                            (pack, pack_field))

        entry_point = content.get('entry_point', None)
        if not entry_point:
            raise ValueError('Sensor definition missing entry_point')

        sensors_dir = os.path.dirname(sensor_metadata_file_path)
        sensor_file_path = os.path.join(sensors_dir, entry_point)
        artifact_uri = 'file://%s' % (sensor_file_path)
        content['artifact_uri'] = artifact_uri
        content['entry_point'] = entry_point

        sensor_api = SensorTypeAPI(**content)
        sensor_model = SensorTypeAPI.to_model(sensor_api)

        sensor_types = SensorType.query(pack=sensor_model.pack, name=sensor_model.name)
        if len(sensor_types) >= 1:
            sensor_type = sensor_types[0]
            LOG.debug('Found existing sensor id:%s with name:%s. Will update it.',
                      sensor_type.id, sensor_type.name)
            sensor_model.id = sensor_type.id

        try:
            sensor_model = SensorType.add_or_update(sensor_model)
        except:
            LOG.exception('Failed creating sensor model for %s', sensor)

        return sensor_model


def register_sensors(packs_base_paths=None, pack_dir=None, use_pack_cache=True,
                     fail_on_failure=False):
    if packs_base_paths:
        assert isinstance(packs_base_paths, list)

    if not packs_base_paths:
        packs_base_paths = content_utils.get_packs_base_paths()

    registrar = SensorsRegistrar(use_pack_cache=use_pack_cache,
                                 fail_on_failure=fail_on_failure)

    if pack_dir:
        result = registrar.register_sensors_from_pack(pack_dir=pack_dir)
    else:
        result = registrar.register_sensors_from_packs(base_dirs=packs_base_paths)

    return result
