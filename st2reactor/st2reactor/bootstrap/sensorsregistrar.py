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
import glob

import six
from oslo.config import cfg

from st2common import log as logging
from st2common.content.loader import ContentPackLoader, MetaLoader
import st2reactor.container.utils as container_utils

__all__ = [
    'SensorsRegistrar',
    'register_sensors'
]

LOG = logging.getLogger(__name__)

PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)))
SYSTEM_SENSORS_PATH = os.path.join(PATH, '../contrib/sensors')
SYSTEM_SENSORS_PATH = os.path.abspath(SYSTEM_SENSORS_PATH)


class SensorsRegistrar(object):
    def __init__(self):
        self._meta_loader = MetaLoader()

    def _get_sensors_from_pack(self, sensors_dir):
        sensors = glob.glob(sensors_dir + '/*.yaml')
        sensors.extend(glob.glob(sensors_dir + '*.yml'))
        return sensors

    def _register_sensors_from_pack(self, pack, sensors):
        for sensor in sensors:
            try:
                self._register_sensor_from_pack(pack=pack, sensor=sensor)
            except Exception as e:
                LOG.debug('Failed to register sensor "%s": %s', sensor, str(e))
            else:
                LOG.debug('Sensor "%s" successfully registered', sensor)

    def _register_sensor_from_pack(self, pack, sensor):
        sensor_metadata_file_path = sensor

        LOG.debug('Loading sensor from %s.', sensor_metadata_file_path)
        metadata = self._meta_loader.load(file_path=sensor_metadata_file_path)

        class_name = metadata.get('class_name', None)
        entry_point = metadata.get('entry_point', None)
        description = metadata.get('description', None)
        trigger_types = metadata.get('trigger_types', [])
        poll_interval = metadata.get('poll_interval', None)

        # Add TrigerType models to the DB
        trigger_type_dbs = container_utils.add_trigger_models(pack=pack,
                                                              trigger_types=trigger_types)

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
                'poll_interval': poll_interval
            }
            container_utils.add_sensor_model(pack=pack, sensor=sensor_obj)

    def register_sensors_from_packs(self, base_dir):
        pack_loader = ContentPackLoader()
        dirs = pack_loader.get_content(base_dir=base_dir, content_type='sensors')

        # Add system sensors to the core pack
        dirs['core'] = {}
        dirs['core'] = SYSTEM_SENSORS_PATH

        for pack, sensors_dir in six.iteritems(dirs):
            try:
                LOG.info('Registering sensors from pack: %s', pack)
                sensors = self._get_sensors_from_pack(sensors_dir)
                self._register_sensors_from_pack(pack=pack, sensors=sensors)
            except Exception as e:
                LOG.exception('Failed registering all sensors from pack "%s": %s', sensors_dir,
                              str(e))


def register_sensors(packs_base_path=None):
    if not packs_base_path:
        packs_base_path = cfg.CONF.content.packs_base_path

    return SensorsRegistrar().register_sensors_from_packs(base_dir=packs_base_path)
