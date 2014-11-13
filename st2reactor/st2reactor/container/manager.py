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
import sys
import six

from st2common import log as logging
from st2common.exceptions.sensors import TriggerTypeRegistrationException
from st2common.persistence.reactor import Trigger
from st2common.util.config_parser import ContentPackConfigParser
from st2common.content.validators import validate_pack_name
from st2common.constants.pack import SYSTEM_PACK_NAME
from st2reactor.container.process_container import MultiProcessSensorContainer
from st2reactor.container.triggerwatcher import TriggerWatcher
import st2reactor.container.utils as container_utils

LOG = logging.getLogger(__name__)


class SensorContainerManager(object):
    # TODO: Load balancing for sensors.
    def __init__(self, max_containers=10):
        self._max_containers = max_containers

    def run_sensors(self, sensors_dict):
        LOG.info('Setting up container to run %d sensors.', len(sensors_dict))
        sensors_to_run = []
        # TODO: Once the API registration is in place, query DB for available
        # sensors here
        # TODO: Use trigger_types and description from sensors metadata
        for filename, sensors in six.iteritems(sensors_dict):
            for sensor_class in sensors:
                class_name = sensor_class.__name__
                sensor_id = class_name

                # System sensors which are not located inside a content pack
                # don't and can't have custom config associated with them
                pack = getattr(sensor_class, 'pack', None)

                if pack:
                    pack = validate_pack_name(name=pack)
                    config_parser = ContentPackConfigParser(pack_name=pack)
                    config_path = config_parser.get_global_config_path()

                    if os.path.isfile(config_path):
                        LOG.info('Using config "%s" for sensor "%s"' % (config_path, class_name))
                    else:
                        LOG.info('No config found for sensor "%s"' % (class_name))
                else:
                    pack = SYSTEM_PACK_NAME
                    config_path = None

                try:
                    trigger_types = sensor_class.get_trigger_types()
                    if not trigger_types:
                        trigger_type_dbs = []
                        LOG.warning('No trigger type registered by sensor %s in file %s',
                                    sensor_class, filename)
                    else:
                        assert isinstance(trigger_types, (list, tuple))
                        trigger_type_dbs = container_utils.add_trigger_models(
                            pack=pack,
                            trigger_types=trigger_types)
                except TriggerTypeRegistrationException as e:
                    LOG.warning('Unable to register trigger type for sensor %s in file %s.'
                                + ' Exception: %s', sensor_class, filename, e, exc_info=True)
                    continue

                # Populate a list of references belonging to this sensor
                trigger_type_refs = []
                for trigger_type_db, _ in trigger_type_dbs:
                    ref_obj = trigger_type_db.get_reference()
                    trigger_type_ref = ref_obj.ref
                    trigger_type_refs.append(trigger_type_ref)

                file_path = os.path.abspath(filename)

                # TODO: Update once lakshmi's PR is merged
                # cfg.CONF.content.packs_base_path
                packs_base_path = '/opt/stackstorm'
                virtualenv_path = os.path.join(packs_base_path,
                                               'virtualenvs/',
                                               pack)

                # Register sensor type in the DB
                sensor_obj = {
                    'file_path': file_path,
                    'name': class_name,
                    'class_name': class_name,
                    'trigger_types': trigger_type_refs
                }
                container_utils.add_sensor_model(pack=pack,
                                                 sensor=sensor_obj)

                # Add good sensor to the run list
                sensor_obj = {
                    'pack': pack,
                    'file_path': file_path,
                    'class_name': class_name,
                    'config_path': config_path,
                    'virtualenv_path': virtualenv_path,
                    'trigger_types': trigger_type_refs
                }

                if pack == 'core':
                    continue
                sensors_to_run.append(sensor_obj)

        for trigger in Trigger.get_all():
            # TODO: Dispatch event to be consumed by the wrapper
            #self._create_handler(trigger=trigger)
            pass

        LOG.info('(PID:%s) SensorContainer started.', os.getpid())
        sensor_container = MultiProcessSensorContainer(sensors=sensors_to_run)
        try:
            exit_code = sensor_container.run()
            LOG.info('(PID:%s) SensorContainer stopped. Reason - run ended.', os.getpid())
            return exit_code
        except (KeyboardInterrupt, SystemExit):
            LOG.info('(PID:%s) SensorContainer stopped. Reason - %s', os.getpid(),
                     sys.exc_info()[0].__name__)
            return 0
