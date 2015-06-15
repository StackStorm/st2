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


import mongoengine as me

from st2common import log as logging
from st2common.models.db import MongoDBAccess
from st2common.models.db import stormbase
from st2common.models.db.notification import NotificationSchema
from st2common.fields import ComplexDateTimeField
from st2common.util import date as date_utils

__all__ = [
    'LiveActionDB',
]

LOG = logging.getLogger(__name__)

PACK_SEPARATOR = '.'


class LiveActionDB(stormbase.StormFoundationDB):
    """
        The databse entity that represents a Stack Action/Automation in
        the system.

        Attributes:
            status: the most recently observed status of the execution.
                    One of "starting", "running", "completed", "error".
            result: an embedded document structure that holds the
                    output and exit status code from the action.
    """

    # TODO: Can status be an enum at the Mongo layer?
    status = me.StringField(
        required=True,
        help_text='The current status of the liveaction.')
    start_timestamp = ComplexDateTimeField(
        default=date_utils.get_datetime_utc_now,
        help_text='The timestamp when the liveaction was created.')
    end_timestamp = ComplexDateTimeField(
        help_text='The timestamp when the liveaction has finished.')
    action = me.StringField(
        required=True,
        help_text='Reference to the action that has to be executed.')
    parameters = me.DictField(
        default={},
        help_text='The key-value pairs passed as to the action runner & execution.')
    result = stormbase.EscapedDynamicField(
        default={},
        help_text='Action defined result.')
    context = me.DictField(
        default={},
        help_text='Contextual information on the action execution.')
    callback = me.DictField(
        default={},
        help_text='Callback information for the on completion of action execution.')
    runner_info = me.DictField(
        default={},
        help_text='Information about the runner which executed this live action (hostname, pid).')
    notify = me.EmbeddedDocumentField(NotificationSchema)

    meta = {
        'indexes': ['-start_timestamp', 'action']
    }

    def to_serializable_dict(self, mask_secrets=False):
        result = super(LiveActionDB, self).to_serializable_dict(mask_secrets=mask_secrets)

        if mask_secrets:
            # TODO: This sucks, but it's only non slow approach
            del result['parameters']

        return result


# specialized access objects
liveaction_access = MongoDBAccess(LiveActionDB)

MODELS = [LiveActionDB]
