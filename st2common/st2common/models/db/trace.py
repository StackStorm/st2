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

from st2common.models.db import stormbase
from st2common.fields import ComplexDateTimeField
from st2common.util import date as date_utils

from st2common.models.db import MongoDBAccess

__all__ = [
    'TraceDB',
    'TraceComponentDB'
]


class TraceComponentDB(me.EmbeddedDocument):
    """
    """
    object_id = me.StringField()
    updated_at = ComplexDateTimeField(
        default=date_utils.get_datetime_utc_now,
        help_text='The timestamp when the TraceComponent was included.')
    caused_by = me.DictField(help_text='Causal component.')

    def __str__(self):
        return 'TraceComponentDB@(object_id:{}, updated_at:{})'.format(
            self.object_id, self.updated_at)


class TraceDB(stormbase.StormFoundationDB):
    """
    Trace is a collection of all TriggerInstances, Rules and ActionExecutions
    that represent an activity which begins with the introduction of a
    TriggerInstance or request of an ActionExecution and ends with the
    completion of an ActionExecution. Given the closed feedback look sort of
    nature of StackStorm this implies a Trace can comprise of multiple
    TriggerInstances, Rules and ActionExecutions.

    :param trace_tag: A user specified reference to the trace.

    :param trigger_instances: TriggerInstances associated with this trace.

    :param rules: Rules associated with this trace.

    :param action_executions: ActionExecutions associated with this trace.
    """
    trace_tag = me.StringField(required=True,
                               help_text='A user specified reference to the trace.')
    trigger_instances = me.ListField(field=me.EmbeddedDocumentField(TraceComponentDB),
                                     required=False,
                                     help_text='Associated TriggerInstances.')
    rules = me.ListField(field=me.EmbeddedDocumentField(TraceComponentDB),
                         required=False,
                         help_text='Associated Rules.')
    action_executions = me.ListField(field=me.EmbeddedDocumentField(TraceComponentDB),
                                     required=False,
                                     help_text='Associated ActionExecutions.')
    start_timestamp = ComplexDateTimeField(default=date_utils.get_datetime_utc_now,
                                           help_text='The timestamp when the Trace was created.')

    meta = {
        'indexes': [
            {'fields': ['trace_tag']},
            {'fields': ['start_timestamp']},
            {'fields': ['action_executions.object_id']},
            {'fields': ['trigger_instances.object_id']},
            {'fields': ['rules.object_id']}
        ]
    }

# specialized access objects
trace_access = MongoDBAccess(TraceDB)

MODELS = [TraceDB]
