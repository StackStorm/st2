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
from six import iteritems
from six.moves import http_client

from st2api.controllers import resource
from st2common import log as logging
from st2common.constants.triggers import TIMER_TRIGGER_TYPES
from st2common.models.api.trigger import TriggerAPI
from st2common.models.system.common import ResourceReference
from st2common.persistence.trigger import Trigger
from st2common.models.db.timer import TimerDB
from st2common.rbac.types import PermissionType
from st2common.rbac.backends import get_rbac_backend
from st2common.services import triggers as trigger_service
from st2common.services.triggerwatcher import TriggerWatcher
from st2common.router import abort

__all__ = [
    'TimersController',
    'TimersHolder'
]


LOG = logging.getLogger(__name__)


class TimersHolder(object):

    def __init__(self):
        self._timers = {}

    def add_trigger(self, ref, trigger):
        self._timers[ref] = trigger

    def remove_trigger(self, ref, trigger):
        del self._timers[ref]

    def get_all(self, timer_type=None):
        timer_triggers = []

        for _, timer in iteritems(self._timers):
            if not timer_type or timer['type'] == timer_type:
                timer_triggers.append(timer)

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

    def __init__(self):
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
        self._allowed_timer_types = TIMER_TRIGGER_TYPES.keys()

    def get_all(self, timer_type=None):
        if timer_type and timer_type not in self._allowed_timer_types:
            msg = 'Timer type %s not in supported types - %s.' % (timer_type,
                                                                  self._allowed_timer_types)
            abort(http_client.BAD_REQUEST, msg)

        t_all = self._timers.get_all(timer_type=timer_type)
        LOG.debug('Got timers: %s', t_all)
        return t_all

    def get_one(self, ref_or_id, requester_user):
        try:
            trigger_db = self._get_by_ref_or_id(ref_or_id=ref_or_id)
        except Exception as e:
            LOG.exception(six.text_type(e))
            abort(http_client.NOT_FOUND, six.text_type(e))
            return

        permission_type = PermissionType.TIMER_VIEW
        resource_db = TimerDB(pack=trigger_db.pack, name=trigger_db.name)

        rbac_utils = get_rbac_backend().get_utils_class()
        rbac_utils.assert_user_has_resource_db_permission(user_db=requester_user,
                                                          resource_db=resource_db,
                                                          permission_type=permission_type)

        result = self.model.from_model(trigger_db)
        return result

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
            LOG.info('Stopped timer %s with parameters %s.', ref, trigger['parameters'])

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


timers_controller = TimersController()
