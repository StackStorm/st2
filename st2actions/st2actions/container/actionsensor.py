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

import httplib

import eventlet
import json
import requests
import requests.exceptions

from oslo.config import cfg
from st2common import log as logging
from st2common.constants.triggers import INTERNAL_TRIGGER_TYPES
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

ACTION_TRIGGER_TYPE = INTERNAL_TRIGGER_TYPES['action'][0]


def _do_register_internal_trigger_types():
    LOG.debug('Registering internal trigger types...')

    for resource_name, trigger_definitions in INTERNAL_TRIGGER_TYPES.items():
        for trigger_definition in trigger_definitions:
            LOG.debug('Registering internal trigger: %s', trigger_definition['name'])
            register_trigger_type(trigger_definition=trigger_definition, attempt_no=0)


def register_trigger_type(trigger_definition, attempt_no=0):
    LOG.debug('Attempt no %s to register trigger %s.', attempt_no, trigger_definition['name'])

    payload = json.dumps(trigger_definition)

    try:
        r = requests.post(TRIGGER_TYPE_ENDPOINT,
                          data=payload,
                          headers=HTTP_POST_HEADER,
                          timeout=TIMEOUT)
        if r.status_code == httplib.CREATED:
            LOG.info('Registered trigger %s.', trigger_definition['name'])
        elif r.status_code == httplib.CONFLICT:
            LOG.info('Trigger %s is already registered.', trigger_definition['name'])
        else:
            LOG.error('Seeing status code %s on an attempt to register trigger %s.',
                      r.status_code, trigger_definition['name'])
    except requests.exceptions.ConnectionError:
        if attempt_no < MAX_ATTEMPTS:
            retry_wait = RETRY_WAIT * (attempt_no + 1)
            LOG.debug('    ConnectionError. Will retry in %ss.', retry_wait)
            eventlet.spawn_after(retry_wait, register_trigger_type,
                                 trigger_definition=trigger_definition,
                                 attempt_no=(attempt_no + 1))
        else:
            LOG.warn('Failed to register trigger %s. Exceeded max attempts to register trigger.',
                     trigger_definition['name'])
    except:
        LOG.exception('Failed to register trigger %s.', trigger_definition['name'])


def register_internal_trigger_types():
    if not ACTION_SENSOR_ENABLED:
        return

    # spawn a thread to process this in order to unblock the main thread which at this point could
    # be in the middle of bootstraping the process.
    eventlet.greenthread.spawn(_do_register_internal_trigger_types)


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

# TODO: This is awful, import shouldn't have side affects
register_internal_trigger_types()
