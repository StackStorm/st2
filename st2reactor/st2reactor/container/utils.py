# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import

from st2common import log as logging
from st2common.constants.triggers import TRIGGER_INSTANCE_PENDING
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.models.db.trigger import TriggerInstanceDB
from st2common.persistence.trigger import TriggerInstance
from st2common.services.triggers import get_trigger_db_by_ref_or_dict

LOG = logging.getLogger("st2reactor.sensor.container_utils")


def create_trigger_instance(
    trigger, payload, occurrence_time, raise_on_no_trigger=False
):
    """
    This creates a trigger instance object given trigger and payload.
    Trigger can be just a string reference (pack.name) or a ``dict`` containing 'id' or
    'uid' or type' and 'parameters' keys.

    :param trigger: Trigger reference or dictionary with trigger query filters.
    :type trigger: ``str`` or ``dict``

    :param payload: Trigger payload.
    :type payload: ``dict``
    """
    trigger_db = get_trigger_db_by_ref_or_dict(trigger=trigger)

    if not trigger_db:
        LOG.debug("No trigger in db for %s", trigger)
        if raise_on_no_trigger:
            raise StackStormDBObjectNotFoundError("Trigger not found for %s" % trigger)
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
