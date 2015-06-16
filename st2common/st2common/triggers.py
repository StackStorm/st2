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
from st2common.constants.triggers import (INTERNAL_TRIGGER_TYPES, ACTION_SENSOR_TRIGGER)
from st2common.models.system.common import ResourceReference
from st2common.services.access import (create_token, delete_token)
from st2common.util.url import get_url_without_trailing_slash

__all__ = [
    'register_internal_trigger_types'
]

LOG = logging.getLogger(__name__)
INTERNAL_TRIGGER_REGISTER_TOKEN_TTL = (1 * 60 * 60)


class InternalTriggerTypesRegistrar(object):

    def __init__(self):
        self._action_sensor_enabled = cfg.CONF.action_sensor.enable
        self._trigger_type_endpoint = cfg.CONF.action_sensor.triggers_base_url
        self._retry_wait = cfg.CONF.action_sensor.retry_wait
        self._timeout = cfg.CONF.action_sensor.request_timeout
        self._max_attempts = cfg.CONF.action_sensor.max_attempts
        self._auth_creds = create_token('system.internal_trigger_registrar',
                                        ttl=INTERNAL_TRIGGER_REGISTER_TOKEN_TTL)
        self._http_post_headers = {'content-type': 'application/json',
                                   'X-Auth-Token': self._auth_creds.token}
        self._http_get_headers = {'X-Auth-Token': self._auth_creds.token}

    def register_internal_trigger_types(self):
        LOG.debug('Registering internal trigger types...')

        for resource_name, trigger_definitions in INTERNAL_TRIGGER_TYPES.items():
            for trigger_definition in trigger_definitions:
                LOG.debug('Registering internal trigger: %s', trigger_definition['name'])
                if (trigger_definition['name'] == ACTION_SENSOR_TRIGGER['name'] and
                        not self._action_sensor_enabled):
                    continue
                self._register_trigger_type(trigger_definition=trigger_definition, attempt_no=0)

        delete_token(self._auth_creds.token)

    def _register_trigger_type(self, trigger_definition, attempt_no=0):
        LOG.debug('Attempt no %s to register trigger %s.', (attempt_no + 1),
                  trigger_definition['name'])

        ref = ResourceReference.to_string_reference(pack=trigger_definition['pack'],
                                                    name=trigger_definition['name'])
        if self._is_triggertype_exists(ref):
            return

        payload = json.dumps(trigger_definition)

        try:
            r = requests.post(url=self._trigger_type_endpoint, data=payload,
                              headers=self._http_post_headers, timeout=self._timeout)
            if r.status_code == httplib.CREATED:
                LOG.info('Registered trigger %s.', trigger_definition['name'])
            elif r.status_code == httplib.CONFLICT:
                LOG.info('Trigger %s is already registered.', trigger_definition['name'])
            else:
                LOG.error('Seeing status code %s on an attempt to register trigger %s.',
                          r.status_code, trigger_definition['name'])
        except requests.exceptions.ConnectionError:
            if attempt_no < self._max_attempts:
                self._retry_wait = self._retry_wait * (attempt_no + 1)
                LOG.debug('    ConnectionError. Will retry in %ss.', self._retry_wait)
                eventlet.spawn_after(self._retry_wait, self._register_trigger_type,
                                     trigger_definition=trigger_definition,
                                     attempt_no=(attempt_no + 1))
            else:
                LOG.warn('Failed to register trigger %s. ' % trigger_definition['name'] +
                         ' Exceeded max attempts to register trigger.')
        except:
            LOG.exception('Failed to register trigger %s.', trigger_definition['name'])

    def _get_trigger_type_url(self, triggertype_ref):
        base_url = get_url_without_trailing_slash(self._trigger_type_endpoint)
        return '%s/%s' % (base_url, triggertype_ref)

    def _is_triggertype_exists(self, ref):
        try:
            r = requests.get(url=self._get_trigger_type_url(ref),
                             headers=self._http_get_headers)
            if r.status_code == httplib.OK:
                return True
        except:
            return False

        return False


def register_internal_trigger_types():
    trigger_types_registrar = InternalTriggerTypesRegistrar()
    # spawn a thread to process this in order to unblock the main thread which at this point could
    # be in the middle of bootstraping the process.
    eventlet.greenthread.spawn(trigger_types_registrar.register_internal_trigger_types)
