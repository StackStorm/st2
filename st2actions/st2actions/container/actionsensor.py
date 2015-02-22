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

from oslo.config import cfg
from st2common import log as logging
from st2common.constants.triggers import INTERNAL_TRIGGER_TYPES
from st2common.models.system.common import ResourceReference
from st2common.transport.reactor import TriggerDispatcher

__all__ = [
    'post_trigger'
]

LOG = logging.getLogger(__name__)

ACTION_SENSOR_ENABLED = cfg.CONF.action_sensor.enable
TRIGGER_DISPATCHER = TriggerDispatcher(LOG)
ACTION_TRIGGER_TYPE = INTERNAL_TRIGGER_TYPES['action'][0]


def post_trigger(liveaction):
    if not ACTION_SENSOR_ENABLED:
        return

    try:
        trigger = ResourceReference.to_string_reference(pack=ACTION_TRIGGER_TYPE['pack'],
                                                        name=ACTION_TRIGGER_TYPE['name'])
        payload = {'execution_id': str(liveaction.id),
                   'status': liveaction.status,
                   'start_timestamp': str(liveaction.start_timestamp),
                   'action_name': liveaction.action,
                   'parameters': liveaction.parameters,
                   'result': liveaction.result}
        LOG.debug('POSTing %s for %s. Payload - %s.', ACTION_TRIGGER_TYPE['name'],
                  liveaction.id, payload)
        TRIGGER_DISPATCHER.dispatch(trigger, payload=payload)
    except:
        LOG.exception('Failed to fire trigger for liveaction %s.', str(liveaction.id))
