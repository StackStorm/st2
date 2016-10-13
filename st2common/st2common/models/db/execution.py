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

import copy

import mongoengine as me

from st2common import log as logging
from st2common.models.db import stormbase
from st2common.fields import ComplexDateTimeField
from st2common.util import date as date_utils
from st2common.util.secrets import get_secret_parameters
from st2common.util.secrets import mask_secret_parameters
from st2common.constants.types import ResourceType

__all__ = [
    'ActionExecutionDB'
]


LOG = logging.getLogger(__name__)


class ActionExecutionDB(stormbase.StormFoundationDB):
    RESOURCE_TYPE = ResourceType.EXECUTION
    UID_FIELDS = ['id']

    trigger = stormbase.EscapedDictField()
    trigger_type = stormbase.EscapedDictField()
    trigger_instance = stormbase.EscapedDictField()
    rule = stormbase.EscapedDictField()
    action = stormbase.EscapedDictField(required=True)
    runner = stormbase.EscapedDictField(required=True)
    # Only the diff between the liveaction type and what is replicated
    # in the ActionExecutionDB object.
    liveaction = stormbase.EscapedDictField(required=True)
    status = me.StringField(
        required=True,
        help_text='The current status of the liveaction.')
    start_timestamp = ComplexDateTimeField(
        default=date_utils.get_datetime_utc_now,
        help_text='The timestamp when the liveaction was created.')
    end_timestamp = ComplexDateTimeField(
        help_text='The timestamp when the liveaction has finished.')
    parameters = stormbase.EscapedDynamicField(
        default={},
        help_text='The key-value pairs passed as to the action runner & action.')
    result = stormbase.EscapedDynamicField(
        default={},
        help_text='Action defined result.')
    context = me.DictField(
        default={},
        help_text='Contextual information on the action execution.')
    parent = me.StringField()
    children = me.ListField(field=me.StringField())
    log = me.ListField(field=me.DictField())
    # Do not use URLField for web_url. If host doesn't have FQDN set, URLField validation blows.
    web_url = me.StringField(required=False)

    meta = {
        'indexes': [
            {'fields': ['rule.ref']},
            {'fields': ['action.ref']},
            {'fields': ['liveaction.id']},
            {'fields': ['start_timestamp']},
            {'fields': ['end_timestamp']},
            {'fields': ['status']},
            {'fields': ['parent']},
            {'fields': ['-start_timestamp', 'action.ref', 'status']}
        ]
    }

    def get_uid(self):
        # TODO Construct od from non id field:
        uid = [self.RESOURCE_TYPE, str(self.id)]
        return ':'.join(uid)

    def mask_secrets(self, value):
        result = copy.deepcopy(value)

        execution_parameters = value['parameters']
        parameters = {}
        # pylint: disable=no-member
        parameters.update(value.get('action', {}).get('parameters', {}))
        parameters.update(value.get('runner', {}).get('runner_parameters', {}))

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


MODELS = [ActionExecutionDB]
