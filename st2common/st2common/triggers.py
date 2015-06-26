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

from oslo_config import cfg

from st2common import log as logging
from st2common.constants.triggers import (INTERNAL_TRIGGER_TYPES, ACTION_SENSOR_TRIGGER)
from st2common.services.triggers import create_trigger_type_db

__all__ = [
    'register_internal_trigger_types'
]

LOG = logging.getLogger(__name__)


def register_internal_trigger_types():
    """
    Register internal trigger types.

    Note: This method blocks until all the trigger types have been registered.
    """
    action_sensor_enabled = cfg.CONF.action_sensor.enable

    for resource_name, trigger_definitions in INTERNAL_TRIGGER_TYPES.items():
        for trigger_definition in trigger_definitions:
            LOG.debug('Registering internal trigger: %s', trigger_definition['name'])

            is_action_trigger = trigger_definition['name'] == ACTION_SENSOR_TRIGGER['name']
            if is_action_trigger and not action_sensor_enabled:
                continue

            create_trigger_type_db(trigger_type=trigger_definition)
            LOG.info('Registered trigger: %s.', trigger_definition['name'])
