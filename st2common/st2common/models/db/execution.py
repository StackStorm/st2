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
from st2common.models.db import stormbase
from st2common.fields import ComplexDateTimeField
from st2common.util import date as date_utils
from st2common.util.secrets import get_secret_parameters
from st2common.util.secrets import mask_inquiry_response
from st2common.util.secrets import mask_secret_parameters
from st2common.constants.types import ResourceType

__all__ = [
    'ActionExecutionDB',
    'ActionExecutionOutputDB'
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
    workflow_execution = me.StringField()
    task_execution = me.StringField()
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
            {'fields': ['rule.name']},
            {'fields': ['runner.name']},
            {'fields': ['trigger.name']},
            {'fields': ['trigger_type.name']},
            {'fields': ['trigger_instance.id']},
            {'fields': ['context.user']},
            {'fields': ['-start_timestamp', 'action.ref', 'status']},
            {'fields': ['workflow_execution']},
            {'fields': ['task_execution']}
        ]
    }

    def get_uid(self):
        # TODO Construct od from non id field:
        uid = [self.RESOURCE_TYPE, str(self.id)]
        return ':'.join(uid)

    def mask_secrets(self, value):
        result = copy.deepcopy(value)

        liveaction = result['liveaction']
        parameters = {}
        # pylint: disable=no-member
        parameters.update(value.get('action', {}).get('parameters', {}))
        parameters.update(value.get('runner', {}).get('runner_parameters', {}))

        secret_parameters = get_secret_parameters(parameters=parameters)
        result['parameters'] = mask_secret_parameters(parameters=result['parameters'],
                                                      secret_parameters=secret_parameters)

        if 'parameters' in liveaction:
            liveaction['parameters'] = mask_secret_parameters(parameters=liveaction['parameters'],
                                                              secret_parameters=secret_parameters)

            if liveaction.get('action', '') == 'st2.inquiry.respond':
                # Special case to mask parameters for `st2.inquiry.respond` action
                # In this case, this execution is just a plain python action, not
                # an inquiry, so we don't natively have a handle on the response
                # schema.
                #
                # To prevent leakage, we can just mask all response fields.
                #
                # Note: The 'string' type in secret_parameters doesn't matter,
                #       it's just a placeholder to tell mask_secret_parameters()
                #       that this parameter is indeed a secret parameter and to
                #       mask it.
                result['parameters']['response'] = mask_secret_parameters(
                    parameters=liveaction['parameters']['response'],
                    secret_parameters={p: 'string' for p in liveaction['parameters']['response']}
                )

        # TODO(mierdin): This logic should be moved to the dedicated Inquiry
        # data model once it exists.
        if self.runner.get('name') == "inquirer":

            schema = result['result'].get('schema', {})
            response = result['result'].get('response', {})

            # We can only mask response secrets if response and schema exist and are
            # not empty
            if response and schema:
                result['result']['response'] = mask_inquiry_response(response, schema)
        return result

    def get_masked_parameters(self):
        """
        Retrieve parameters with the secrets masked.

        :rtype: ``dict``
        """
        serializable_dict = self.to_serializable_dict(mask_secrets=True)
        return serializable_dict['parameters']


class ActionExecutionOutputDB(stormbase.StormFoundationDB):
    """
    Stores output of a particular execution.

    New document is inserted dynamically when a new chunk / line is received which means you can
    simulate tail behavior by periodically reading from this collection.

    Attribute:
        execution_id: ID of the execution to which this output belongs.
        action_ref: Parent action reference.
        runner_ref: Parent action runner reference.
        timestamp: Timestamp when this output has been produced / received.
        output_type: Type of the output (e.g. stdout, stderr, output)
        data: Actual output data. This could either be line, chunk or similar, depending on the
              runner.
    """
    execution_id = me.StringField(required=True)
    action_ref = me.StringField(required=True)
    runner_ref = me.StringField(required=True)
    timestamp = ComplexDateTimeField(required=True, default=date_utils.get_datetime_utc_now)
    output_type = me.StringField(required=True, default='output')

    data = me.StringField()

    meta = {
        'indexes': [
            {'fields': ['execution_id']},
            {'fields': ['action_ref']},
            {'fields': ['runner_ref']},
            {'fields': ['timestamp']},
            {'fields': ['output_type']}
        ]
    }


MODELS = [ActionExecutionDB, ActionExecutionOutputDB]
