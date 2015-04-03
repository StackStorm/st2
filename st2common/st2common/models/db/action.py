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

import datetime
import mongoengine as me

from st2common import log as logging
from st2common.models.db import MongoDBAccess
from st2common.models.db import stormbase
from st2common.fields import ComplexDateTimeField

__all__ = [
    'RunnerTypeDB',
    'ActionDB',
    'LiveActionDB'
]


LOG = logging.getLogger(__name__)

PACK_SEPARATOR = '.'


class RunnerTypeDB(stormbase.StormBaseDB):
    """
    The representation of an RunnerType in the system. An RunnerType
    has a one-to-one mapping to a particular ActionRunner implementation.

    Attributes:
        id: See StormBaseAPI
        name: See StormBaseAPI
        description: See StormBaseAPI
        enabled: A flag indicating whether the runner for this type is enabled.
        runner_module: The python module that implements the action runner for this type.
        runner_parameters: The specification for parameters for the action runner.
    """

    enabled = me.BooleanField(
        required=True, default=True,
        help_text='A flag indicating whether the runner for this type is enabled.')
    runner_module = me.StringField(
        required=True,
        help_text='The python module that implements the action runner for this type.')
    runner_parameters = me.DictField(
        help_text='The specification for parameters for the action runner.')
    query_module = me.StringField(
        required=False,
        help_text='The python module that implements the query module for this runner.')


class ActionDB(stormbase.StormFoundationDB, stormbase.TagsMixin,
               stormbase.ContentPackResourceMixin):
    """
    The system entity that represents a Stack Action/Automation in the system.

    Attribute:
        enabled: A flag indicating whether this action is enabled in the system.
        entry_point: The entry point to the action.
        runner_type: The actionrunner is used to execute the action.
        parameters: The specification for parameters for the action.
    """
    name = me.StringField(required=True)
    ref = me.StringField(required=True)
    description = me.StringField()
    enabled = me.BooleanField(
        required=True, default=True,
        help_text='A flag indicating whether the action is enabled.')
    entry_point = me.StringField(
        required=True,
        help_text='The entry point to the action.')
    pack = me.StringField(
        required=False,
        help_text='Name of the content pack.',
        unique_with='name')
    runner_type = me.DictField(
        required=True, default={},
        help_text='The action runner to use for executing the action.')
    parameters = me.DictField(
        help_text='The specification for parameters for the action.')

    meta = {
        'indexes': stormbase.TagsMixin.get_indices()
    }


class NotificationSubSchema(me.EmbeddedDocument):
    """
        Schema for notification settings to be specified for action success/failure.
    """
    message = me.StringField()
    data = stormbase.EscapedDynamicField(
        default={},
        help_text='Payload to be sent as part of notification.')
    triggers = me.ListField(
        default=['notify.default'],
        help_text='Triggers to be emitted for notifications.')

    def __str__(self):
        result = []
        result.append('NotificationSubSchema@')
        result.append(str(id(self)))
        result.append('(message="%s", ' % str(self.message))
        result.append('data="%s", ' % str(self.data))
        result.append('triggers="%s")' % str(self.triggers))
        return ''.join(result)


class NotificationSchema(me.EmbeddedDocument):
    """
        Schema for notification settings to be specified for actions.
    """
    on_success = me.EmbeddedDocumentField(NotificationSubSchema)
    on_failure = me.EmbeddedDocumentField(NotificationSubSchema)

    # XXX: This is nasty. I don't see an easy way to get fields from
    # NotificationSubSchema and make it members of this Document.
    message = me.StringField()
    data = stormbase.EscapedDynamicField(
        default={},
        help_text='Payload to be sent as part of notification.')
    triggers = me.ListField(
        default=['notify.default'],
        help_text='Triggers to be emitted for notifications.')

    def __str__(self):
        result = []
        result.append('NotifySchema@')
        result.append(str(id(self)))
        result.append('(message="%s", ' % self.message)
        result.append('data="%s", ' % str(self.data))
        result.append('triggers="%s", ' % str(self.triggers))
        result.append('on_success="%s", ' % str(self.on_success))
        result.append('on_failure="%s")' % str(self.on_failure))
        return ''.join(result)


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
        default=datetime.datetime.utcnow,
        help_text='The timestamp when the liveaction was created.')
    end_timestamp = ComplexDateTimeField(
        help_text='The timestamp when the liveaction has finished.')
    action = me.StringField(
        required=True,
        help_text='Reference to the action that has to be executed.')
    parameters = me.DictField(
        default={},
        help_text='The key-value pairs passed as to the action runner &  execution.')
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
        help_text='Reference to the runner that executed this liveaction.')
    notify = me.EmbeddedDocumentField(NotificationSchema)

    def __init__(self, *args, **kwargs):
        super(LiveActionDB, self).__init__(*args, **kwargs)
        self.notify = self.get_default_notification_settings()

    meta = {
        'indexes': ['-start_timestamp', 'action']
    }

    def get_default_notification_settings(self):
        print('Constructing default notification settings.')
        notification_schema = NotificationSchema()
        on_success_default = NotificationSubSchema()
        if self.action:
            on_success_default.message = 'Action ' + self.action + ' succeeded.'
        else:
            # XXX: This is a problem. Sometimes we don't set the action name until later.
            # See for example, executions API. We can use something like
            # http://mongoengine-odm.readthedocs.org/guide/signals.html but it will be mongo
            # specific.
            on_success_default.message = 'Action succeeded.'
        on_failure_default = NotificationSubSchema()
        if self.action:
            on_failure_default.message = 'Action ' + self.action + ' failed.'
        else:
            on_failure_default.message = 'Action failed.'
        notification_schema.on_success = on_success_default
        notification_schema.on_failure = on_failure_default
        return notification_schema


class ActionExecutionStateDB(stormbase.StormFoundationDB):
    """
        Database entity that represents the state of Action execution.
    """

    execution_id = me.ObjectIdField(
        required=True,
        unique=True,
        help_text='liveaction ID.')
    query_module = me.StringField(
        required=True,
        help_text='Reference to the runner model.')
    query_context = me.DictField(
        required=True,
        help_text='Context about the action execution that is needed for results query.')

    meta = {
        'indexes': ['query_module']
    }

# specialized access objects
runnertype_access = MongoDBAccess(RunnerTypeDB)
action_access = MongoDBAccess(ActionDB)
liveaction_access = MongoDBAccess(LiveActionDB)
actionexecstate_access = MongoDBAccess(ActionExecutionStateDB)

MODELS = [RunnerTypeDB, ActionDB, LiveActionDB, ActionExecutionStateDB]
