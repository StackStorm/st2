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
from st2common.util import isotime
from st2common.models.db import stormbase
from st2common.fields import ComplexDateTimeField

__all__ = [
    'ActionExecutionDB'
]


LOG = logging.getLogger(__name__)


class ActionExecutionDB(stormbase.StormFoundationDB):
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
        default=isotime.get_datetime_utc_now,
        help_text='The timestamp when the liveaction was created.')
    end_timestamp = ComplexDateTimeField(
        help_text='The timestamp when the liveaction has finished.')
    parameters = me.DictField(
        default={},
        help_text='The key-value pairs passed as to the action runner &  execution.')
    result = stormbase.EscapedDynamicField(
        default={},
        help_text='Action defined result.')
    context = me.DictField(
        default={},
        help_text='Contextual information on the action execution.')
    parent = me.StringField()
    children = me.ListField(field=me.StringField())

    meta = {
        'indexes': [
            {'fields': ['parent']},
            {'fields': ['liveaction.id']},
            {'fields': ['start_timestamp']},
            {'fields': ['action.ref']},
            {'fields': ['status']}
        ]
    }

MODELS = [ActionExecutionDB]
