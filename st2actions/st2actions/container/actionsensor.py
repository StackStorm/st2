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

import eventlet
import json
import requests
import requests.exceptions

from oslo.config import cfg
from st2common import log as logging
from st2common.constants.pack import SYSTEM_PACK_NAME
from st2common.models.system.common import ResourceReference
from st2common.transport.reactor import TriggerDispatcher

ACTION_SENSOR_ENABLED = cfg.CONF.action_sensor.enable
TRIGGER_TYPE_ENDPOINT = cfg.CONF.action_sensor.triggers_base_url
TRIGGER_INSTANCE_ENDPOINT = cfg.CONF.action_sensor.webhook_sensor_base_url
TIMEOUT = cfg.CONF.action_sensor.request_timeout
MAX_ATTEMPTS = cfg.CONF.action_sensor.max_attempts
RETRY_WAIT = cfg.CONF.action_sensor.retry_wait
HTTP_POST_HEADER = {'content-type': 'application/json'}

LOG = logging.getLogger(__name__)
TRIGGER_DISPATCHER = TriggerDispatcher(LOG)

ACTION_TRIGGER_TYPE = {
    'name': 'st2.generic.actiontrigger',
    'pack': SYSTEM_PACK_NAME,
    'description': 'Trigger encapsulating the completion of an action execution.',
    'payload_schema': {
        'type': 'object',
        'properties': {
            'execution_id': {},
            'status': {},
            'start_timestamp': {},
            'action_name': {},
            'parameters': {},
            'result': {}
        }
    }
}


def _do_register_trigger_type(attempt_no=0):
    LOG.debug('Attempt no %s to register %s.', attempt_no, ACTION_TRIGGER_TYPE['name'])
    try:
        payload = json.dumps(ACTION_TRIGGER_TYPE)
        r = requests.post(TRIGGER_TYPE_ENDPOINT,
                          data=payload,
                          headers=HTTP_POST_HEADER,
                          timeout=TIMEOUT)
        if r.status_code == 201:
            LOG.info('Registered trigger %s.', ACTION_TRIGGER_TYPE['name'])
        elif r.status_code == 409:
            LOG.info('Trigger %s is already registered.', ACTION_TRIGGER_TYPE['name'])
        else:
            LOG.error('Seeing status code %s on an attempt to register trigger %s.',
                      r.status_code, ACTION_TRIGGER_TYPE['name'])
    except requests.exceptions.ConnectionError:
        if attempt_no < MAX_ATTEMPTS:
            retry_wait = RETRY_WAIT * (attempt_no + 1)
            LOG.debug('    ConnectionError. Will retry in %ss.', retry_wait)
            eventlet.spawn_after(retry_wait, _do_register_trigger_type, attempt_no + 1)
        else:
            LOG.warn('Failed to register trigger %s. Exceeded max attempts to register trigger.',
                     ACTION_TRIGGER_TYPE['name'])
    except:
        LOG.exception('Failed to register trigger %s.', ACTION_TRIGGER_TYPE['name'])


def register_trigger_type():
    if not ACTION_SENSOR_ENABLED:
        return
    # spawn a thread to process this in order to unblock the main thread which at this point could
    # be in the middle of bootstraping the process.
    eventlet.greenthread.spawn(_do_register_trigger_type)


def post_trigger(action_execution):
    if not ACTION_SENSOR_ENABLED:
        return
    try:
        trigger = ResourceReference.to_string_reference(pack=ACTION_TRIGGER_TYPE['pack'],
                                                        name=ACTION_TRIGGER_TYPE['name'])
        payload = {'execution_id': str(action_execution.id),
                   'status': action_execution.status,
                   'start_timestamp': str(action_execution.start_timestamp),
                   'action_name': action_execution.action,
                   'parameters': action_execution.parameters,
                   'result': action_execution.result}
        LOG.debug('POSTing %s for %s. Payload - %s.', ACTION_TRIGGER_TYPE['name'],
                  action_execution.id, payload)
        TRIGGER_DISPATCHER.dispatch(trigger, payload=payload)
    except:
        LOG.exception('Failed to fire trigger for action_execution %s.', str(action_execution.id))

register_trigger_type()
