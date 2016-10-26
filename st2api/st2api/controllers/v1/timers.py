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

import six

from st2api.controllers import resource
from st2common import log as logging
from st2common.constants.triggers import TIMER_TRIGGER_TYPES
from st2common.models.api.base import jsexpose
from st2common.models.api.trigger import TriggerAPI
from st2common.models.system.common import ResourceReference
from st2common.persistence.trigger import Trigger
import st2common.services.triggers as trigger_service
from st2common.services.triggerwatcher import TriggerWatcher

LOG = logging.getLogger(__name__)


class TimersHolder(object):

    def __init__(self):
        self._timers = {}

    def add_trigger(self, ref, trigger):
        self._timers[ref] = trigger

    def remove_trigger(self, ref, trigger):
        del self._timers[ref]

    def get_all(self):
        timer_triggers = []

        LOG.info('Timers: %s', self._timers)

        for _, timer in six.iteritems(self._timers):
            LOG.info('Appending timer: %s', timer)
            timer_triggers.append(timer)

        LOG.info('Returning timers: %s', timer_triggers)
        return timer_triggers



class TimersController(resource.ContentPackResourceController):
    model = TriggerAPI
    access = Trigger

    supported_filters = {
        'type': 'type',
    }

    query_options = {
        'sort': ['type']
    }

    def __init__(self, *args, **kwargs):
        self._timers = TimersHolder()
        self._trigger_types = TIMER_TRIGGER_TYPES.keys()
        queue_suffix = self.__class__.__name__
        self._trigger_watcher = TriggerWatcher(create_handler=self._handle_create_trigger,
                                               update_handler=self._handle_update_trigger,
                                               delete_handler=self._handle_delete_trigger,
                                               trigger_types=self._trigger_types,
                                               queue_suffix=queue_suffix,
                                               exclusive=True)
        self._trigger_watcher.start()
        self._register_timer_trigger_types()

    @jsexpose()
    def get_all(self):
        t_all = self._timers.get_all()
        LOG.info('Got timers: %s', t_all)
        return t_all

    def add_trigger(self, trigger):
        # Note: Permission checking for creating and deleting a timer is done during rule
        # creation
        ref = self._get_timer_ref(trigger)
        LOG.info('Started timer %s with parameters %s', ref, trigger['parameters'])
        self._timers.add_trigger(ref, trigger)

    def update_trigger(self, trigger):
        pass

    def remove_trigger(self, trigger):
        # Note: Permission checking for creating and deleting a timer is done during rule
        # creation
        ref = self._get_timer_ref(trigger)

        removed = self._timers.remove_trigger(ref, trigger)
        if removed:
            LOG.info('Stopped timer %s with parameters', ref, trigger['parameters'])

    def _register_timer_trigger_types(self):
        for trigger_type in TIMER_TRIGGER_TYPES.values():
            trigger_service.create_trigger_type_db(trigger_type)

    def _get_timer_ref(self, trigger):
        return ResourceReference.to_string_reference(pack=trigger['pack'], name=trigger['name'])

    ##############################################
    # Event handler methods for the trigger events
    ##############################################

    def _handle_create_trigger(self, trigger):
        LOG.debug('Calling "add_trigger" method (trigger.type=%s)' % (trigger.type))
        trigger = self._sanitize_trigger(trigger=trigger)
        self.add_trigger(trigger=trigger)

    def _handle_update_trigger(self, trigger):
        LOG.debug('Calling "update_trigger" method (trigger.type=%s)' % (trigger.type))
        trigger = self._sanitize_trigger(trigger=trigger)
        self.update_trigger(trigger=trigger)

    def _handle_delete_trigger(self, trigger):
        LOG.debug('Calling "remove_trigger" method (trigger.type=%s)' % (trigger.type))
        trigger = self._sanitize_trigger(trigger=trigger)
        self.remove_trigger(trigger=trigger)

    def _sanitize_trigger(self, trigger):
        sanitized = TriggerAPI.from_model(trigger).to_dict()
        return sanitized
