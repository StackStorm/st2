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

from __future__ import absolute_import
import copy

import mongoengine as me

from st2common import log as logging
from st2common.models.db import MongoDBAccess
from st2common.models.db import stormbase
from st2common.models.db.notification import NotificationSchema
from st2common.fields import ComplexDateTimeField
from st2common.util import date as date_utils
from st2common.util.secrets import get_secret_parameters
from st2common.util.secrets import mask_secret_parameters

__all__ = [
    'LiveActionDB',
]

LOG = logging.getLogger(__name__)

PACK_SEPARATOR = '.'


class LiveActionDB(stormbase.StormFoundationDB):
    workflow_execution = me.StringField()
    task_execution = me.StringField()
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
    action_is_workflow = me.BooleanField(
        default=False,
        help_text='A flag indicating whether the referenced action is a workflow.')
    parameters = stormbase.EscapedDynamicField(
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
        'indexes': [
            {'fields': ['-start_timestamp', 'action']},
            {'fields': ['start_timestamp']},
            {'fields': ['end_timestamp']},
            {'fields': ['action']},
            {'fields': ['status']},
            {'fields': ['context.trigger_instance.id']},
            {'fields': ['workflow_execution']},
            {'fields': ['task_execution']}
        ]
    }

    def mask_secrets(self, value):
        from st2common.util import action_db

        result = copy.deepcopy(value)
        execution_parameters = value['parameters']

        # TODO: This results into two DB looks, we should cache action and runner type object
        # for each liveaction...
        #
        #       ,-'"-.
        # .    f .--. \
        # .\._,\._',' j_
        #  7______""-'__`,
        parameters = action_db.get_action_parameters_specs(action_ref=self.action)

        secret_parameters = get_secret_parameters(parameters=parameters)
        result['parameters'] = mask_secret_parameters(parameters=execution_parameters,
                                                      secret_parameters=secret_parameters)
        return result

    def get_masked_parameters(self):
        """
        Retrieve parameters with the secrets masked.

        :rtype: ``dict``
        """
        serializable_dict = self.to_serializable_dict(mask_secrets=True)
        return serializable_dict['parameters']


# specialized access objects
liveaction_access = MongoDBAccess(LiveActionDB)

MODELS = [LiveActionDB]
