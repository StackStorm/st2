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

__all__ = [
    'register_internal_trigger_types'
]

LOG = logging.getLogger(__name__)

ACTION_SENSOR_ENABLED = cfg.CONF.action_sensor.enable
TRIGGER_TYPE_ENDPOINT = cfg.CONF.action_sensor.triggers_base_url
HTTP_POST_HEADER = {'content-type': 'application/json'}
RETRY_WAIT = cfg.CONF.action_sensor.retry_wait
TIMEOUT = cfg.CONF.action_sensor.request_timeout
MAX_ATTEMPTS = cfg.CONF.action_sensor.max_attempts


def _get_trigger_type_url(triggertype_ref):
    if TRIGGER_TYPE_ENDPOINT.endswith('/'):
        return TRIGGER_TYPE_ENDPOINT + triggertype_ref
    else:
        return '%s/%s' % (TRIGGER_TYPE_ENDPOINT, triggertype_ref)


def _do_register_internal_trigger_types():
    LOG.debug('Registering internal trigger types...')

    for resource_name, trigger_definitions in INTERNAL_TRIGGER_TYPES.items():
        for trigger_definition in trigger_definitions:
            LOG.debug('Registering internal trigger: %s', trigger_definition['name'])
            register_trigger_type(trigger_definition=trigger_definition, attempt_no=0)


def _is_triggertype_exists(ref):
    try:
        r = requests.get(url=_get_trigger_type_url(ref))
        if r.status_code == httplib.OK:
            return True
    except:
        return False


def register_trigger_type(trigger_definition, attempt_no=0):
    LOG.debug('Attempt no %s to register trigger %s.', attempt_no, trigger_definition['name'])

    ref = ResourceReference.to_string_reference(pack=trigger_definition['pack'],
                                                name=trigger_definition['name'])
    if _is_triggertype_exists(ref):
        return

    payload = json.dumps(trigger_definition)

    try:
        r = requests.post(url=TRIGGER_TYPE_ENDPOINT, data=payload,
                          headers=HTTP_POST_HEADER, timeout=TIMEOUT)
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
