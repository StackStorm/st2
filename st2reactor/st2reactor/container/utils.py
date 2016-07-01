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

from st2common import log as logging
from st2common.constants.triggers import TRIGGER_INSTANCE_PENDING
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.models.db.trigger import TriggerInstanceDB
from st2common.persistence.trigger import TriggerInstance
from st2common.services import triggers as TriggerService

LOG = logging.getLogger('st2reactor.sensor.container_utils')


def create_trigger_instance(trigger, payload, occurrence_time, raise_on_no_trigger=False):
    """
    This creates a trigger instance object given trigger and payload.
    Trigger can be just a string reference (pack.name) or a ``dict`` containing 'id' or
    'uid' or type' and 'parameters' keys.

    :param trigger: Trigger reference or dictionary with trigger query filters.
    :type trigger: ``str`` or ``dict``

    :param payload: Trigger payload.
    :type payload: ``dict``
    """
    # TODO: This is nasty, this should take a unique reference and not a dict
    if isinstance(trigger, six.string_types):
        trigger_db = TriggerService.get_trigger_db_by_ref(trigger)
    else:
        # If id / uid is available we try to look up Trigger by id. This way we can avoid bug in
        # pymongo / mongoengine related to "parameters" dictionary lookups
        trigger_id = trigger.get('id', None)
        trigger_uid = trigger.get('uid', None)

        # TODO: Remove parameters dictionary look up when we can confirm each trigger dictionary
        # passed to this method always contains id or uid
        if trigger_id:
            LOG.debug('Looking up TriggerDB by id: %s', trigger_id)
            trigger_db = TriggerService.get_trigger_db_by_id(id=trigger_id)
        elif trigger_uid:
            LOG.debug('Looking up TriggerDB by uid: %s', trigger_uid)
            trigger_db = TriggerService.get_trigger_db_by_uid(uid=trigger_uid)
        else:
            # Last resort - look it up by parameters
            trigger_type = trigger.get('type', None)
            parameters = trigger.get('parameters', {})

            LOG.debug('Looking up TriggerDB by type and parameters: type=%s, parameters=%s',
                      trigger_type, parameters)
            trigger_db = TriggerService.get_trigger_db_given_type_and_params(type=trigger_type,
                                                                             parameters=parameters)

    if trigger_db is None:
        LOG.debug('No trigger in db for %s', trigger)
        if raise_on_no_trigger:
            raise StackStormDBObjectNotFoundError('Trigger not found for %s', trigger)
        return None

    trigger_ref = trigger_db.get_reference().ref

    trigger_instance = TriggerInstanceDB()
    trigger_instance.trigger = trigger_ref
    trigger_instance.payload = payload
    trigger_instance.occurrence_time = occurrence_time
    trigger_instance.status = TRIGGER_INSTANCE_PENDING
    return TriggerInstance.add_or_update(trigger_instance)


def update_trigger_instance_status(trigger_instance, status):
    trigger_instance.status = status
    return TriggerInstance.add_or_update(trigger_instance)
